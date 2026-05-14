"""
Backend Stack for Know-It-All Tutor System
Contains Lambda functions and API Gateway
"""
import json
import subprocess
import shutil
from pathlib import Path
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_ecr_assets as ecr_assets,
    custom_resources as cr,
    Duration,
    CfnOutput
)
from constructs import Construct


class LocalBundler(cdk.ILocalBundling):
    """Local bundling for Lambda functions - avoids Docker-in-Docker issues"""
    
    def __init__(self, source_dir: str):
        self.source_dir = Path(source_dir)
    
    def try_bundle(self, output_dir: str, options: cdk.BundlingOptions) -> bool:
        """
        Try to bundle locally using pip install on the host.
        Returns True if successful, False to fall back to Docker.
        """
        try:
            # Install dependencies
            subprocess.run(
                ["pip3", "install", "-r", str(self.source_dir / "requirements.txt"), "-t", output_dir],
                check=True,
                capture_output=True
            )
            
            # Copy handler
            shutil.copy2(self.source_dir / "handler.py", output_dir)
            
            # Copy migrations if they exist
            migrations_src = self.source_dir / "migrations"
            if migrations_src.exists():
                migrations_dest = Path(output_dir) / "opt" / "migrations"
                migrations_dest.mkdir(parents=True, exist_ok=True)
                for sql_file in migrations_src.glob("*.sql"):
                    shutil.copy2(sql_file, migrations_dest)
            
            return True
        except Exception as e:
            print(f"Local bundling failed: {e}")
            return False


class BackendStack(Stack):
    """
    Backend infrastructure stack containing Lambda functions and API Gateway.
    This stack changes frequently.
    """
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        network_stack,
        database_stack,
        auth_stack,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Store auth_stack reference
        self.auth_stack = auth_stack
        
        # Import resources from other stacks
        self.vpc = network_stack.vpc
        self.lambda_security_group = network_stack.lambda_security_group
        self.database = database_stack.database
        self.db_credentials = database_stack.db_credentials
        self.user_pool = auth_stack.user_pool
        self.user_pool_client = auth_stack.user_pool_client
        
        # Create Lambda Layer for shared utilities
        self.shared_layer = _lambda.LayerVersion(
            self,
            "SharedUtilitiesLayer",
            code=_lambda.Code.from_asset("lambda_layer"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description="Shared utilities for authentication and security"
        )
        
        # Create DB Proxy Lambda (inside VPC)
        self.db_proxy_lambda = _lambda.Function(
            self,
            "DBProxyFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/db_proxy"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[self.lambda_security_group],
            environment={
                "DB_HOST": self.database.db_instance_endpoint_address,
                "DB_PORT": "5432",
                "DB_NAME": "tutor_system",
                "DB_USER": self.db_credentials.secret_value_from_json("username").unsafe_unwrap(),
                "DB_PASSWORD": self.db_credentials.secret_value_from_json("password").unsafe_unwrap(),
            },
            description="Database proxy Lambda - handles all DB operations from VPC"
        )
        
        # Create Migration Runner Lambda (inside VPC)
        self.migration_runner_lambda = _lambda.Function(
            self,
            "MigrationRunnerFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/migration_runner"),
            timeout=Duration.seconds(300),  # 5 minutes for migrations
            memory_size=512,
            layers=[self.shared_layer],
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[self.lambda_security_group],
            environment={
                "DB_HOST": self.database.db_instance_endpoint_address,
                "DB_PORT": "5432",
                "DB_NAME": "tutor_system",
                "DB_USER": self.db_credentials.secret_value_from_json("username").unsafe_unwrap(),
                "DB_PASSWORD": self.db_credentials.secret_value_from_json("password").unsafe_unwrap(),
                "MIGRATIONS_DIR": "/var/task/migrations"
            },
            description="Database migration runner - applies schema migrations"
        )
        
        # Run migrations on deployment using Custom Resource
        migration_trigger = cr.AwsCustomResource(
            self,
            "MigrationTrigger",
            on_create=cr.AwsSdkCall(
                service="Lambda",
                action="invoke",
                parameters={
                    "FunctionName": self.migration_runner_lambda.function_name,
                    "Payload": json.dumps({"action": "migrate"})
                },
                physical_resource_id=cr.PhysicalResourceId.of("MigrationTrigger")
            ),
            on_update=cr.AwsSdkCall(
                service="Lambda",
                action="invoke",
                parameters={
                    "FunctionName": self.migration_runner_lambda.function_name,
                    "Payload": json.dumps({"action": "migrate"})
                },
                physical_resource_id=cr.PhysicalResourceId.of("MigrationTrigger")
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(
                    actions=["lambda:InvokeFunction"],
                    resources=[self.migration_runner_lambda.function_arn]
                )
            ])
        )
        
        # Ensure migrations run before other Lambdas are created
        migration_trigger.node.add_dependency(self.migration_runner_lambda)
        
        # Create Auth Lambda (outside VPC)
        self.auth_lambda = _lambda.Function(
            self,
            "AuthFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/auth"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            environment={
                "USER_POOL_ID": self.user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": self.user_pool_client.user_pool_client_id,
                "STAGE": "prod",
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
                "AWS_CA_BUNDLE": "/etc/pki/tls/certs/ca-bundle.crt",
            },
            description="Auth Lambda - handles Cognito, invokes DB proxy"
        )
        self.user_pool.grant(self.auth_lambda, "cognito-idp:AdminConfirmSignUp", "cognito-idp:AdminGetUser")
        self.db_proxy_lambda.grant_invoke(self.auth_lambda)
        
        # Create User Profile Lambda
        self.profile_lambda = _lambda.Function(
            self,
            "ProfileFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/user_profile"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
                "AWS_CA_BUNDLE": "/etc/pki/tls/certs/ca-bundle.crt",
            },
            description="User profile management"
        )
        self.db_proxy_lambda.grant_invoke(self.profile_lambda)
        
        # Create Domain Management Lambda
        self.domain_lambda = _lambda.Function(
            self,
            "DomainFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/domain_management"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
                "AWS_CA_BUNDLE": "/etc/pki/tls/certs/ca-bundle.crt",
            },
            description="Domain management operations"
        )
        self.db_proxy_lambda.grant_invoke(self.domain_lambda)
        
        # Create Progress Tracking Lambda
        self.progress_lambda = _lambda.Function(
            self,
            "ProgressFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/progress_tracking"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
                "AWS_CA_BUNDLE": "/etc/pki/tls/certs/ca-bundle.crt",
            },
            description="Progress tracking operations"
        )
        self.db_proxy_lambda.grant_invoke(self.progress_lambda)
        
        # Create Batch Upload Lambda
        self.batch_upload_lambda = _lambda.Function(
            self,
            "BatchUploadFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/batch_upload"),
            timeout=Duration.seconds(60),
            memory_size=512,
            layers=[self.shared_layer],
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
                "AWS_CA_BUNDLE": "/etc/pki/tls/certs/ca-bundle.crt",
            },
            description="Batch upload validation and processing"
        )
        self.db_proxy_lambda.grant_invoke(self.batch_upload_lambda)
        
        # Create Quiz Engine Lambda
        self.quiz_engine_lambda = _lambda.Function(
            self,
            "QuizEngineFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/quiz_engine"),
            timeout=Duration.seconds(30),
            memory_size=512,
            layers=[self.shared_layer],
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
                "AWS_CA_BUNDLE": "/etc/pki/tls/certs/ca-bundle.crt",
            },
            description="Quiz engine - manages quiz sessions"
        )
        self.db_proxy_lambda.grant_invoke(self.quiz_engine_lambda)
        
        # Create Answer Evaluator Lambda (container-based with ML model)
        self.answer_evaluator_lambda = _lambda.DockerImageFunction(
            self,
            "AnswerEvaluatorFunction",
            code=_lambda.DockerImageCode.from_image_asset(
                "..",  # Build from project root (needed for final_similarity_model/)
                file="lambda/answer-evaluator/Dockerfile",
                exclude=[
                    "infrastructure/cdk.out",
                    "infrastructure/.venv",
                    "frontend/node_modules",
                    "frontend/dist",
                    ".git",
                    ".ci-venv",
                    "**/__pycache__",
                    "**/*.pyc",
                    "src",
                    "tests",
                    "artifacts",
                    ".kiro",
                    "scripts",
                ]
            ),
            timeout=Duration.seconds(60),
            memory_size=2048,
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
                "AWS_CA_BUNDLE": "/etc/pki/tls/certs/ca-bundle.crt",
            },
            description="Answer evaluator with ML model"
        )
        self.db_proxy_lambda.grant_invoke(self.answer_evaluator_lambda)
        
        # Create API Gateway
        self.api = apigateway.RestApi(
            self,
            "TutorAPI",
            rest_api_name="know-it-all-tutor-api-multistack-dev",
            description="API for Know-It-All Tutor System",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["https://d3awlgby2429wc.cloudfront.net"],
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "X-Amz-Date",
                    "X-Api-Key",
                    "X-Amz-Security-Token"
                ],
                allow_credentials=True
            ),
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,
                throttling_burst_limit=200
            )
        )
        
        # Add CORS headers to error responses (401, 403, 500, etc.)
        cors_headers = {
            "Access-Control-Allow-Origin": "'https://d3awlgby2429wc.cloudfront.net'",
            "Access-Control-Allow-Credentials": "'true'"
        }
        
        self.api.add_gateway_response(
            "Unauthorized",
            type=apigateway.ResponseType.UNAUTHORIZED,
            response_headers=cors_headers
        )
        self.api.add_gateway_response(
            "AccessDenied",
            type=apigateway.ResponseType.ACCESS_DENIED,
            response_headers=cors_headers
        )
        self.api.add_gateway_response(
            "Default4XX",
            type=apigateway.ResponseType.DEFAULT_4_XX,
            response_headers=cors_headers
        )
        self.api.add_gateway_response(
            "Default5XX",
            type=apigateway.ResponseType.DEFAULT_5_XX,
            response_headers=cors_headers
        )
        
        # Create Cognito Authorizer
        authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuthorizer",
            cognito_user_pools=[self.user_pool]
        )
        
        # Add API routes
        # Auth routes (no authorization)
        auth_resource = self.api.root.add_resource("auth")
        auth_resource.add_resource("register").add_method(
            "POST",
            apigateway.LambdaIntegration(self.auth_lambda)
        )
        auth_resource.add_resource("login").add_method(
            "POST",
            apigateway.LambdaIntegration(self.auth_lambda)
        )
        
        # Profile routes (with authorization)
        profile_resource = self.api.root.add_resource("profile")
        profile_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.profile_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # Domain routes (with authorization)
        domains_resource = self.api.root.add_resource("domains")
        domains_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.domain_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # Batch Upload routes (with authorization)
        batch_resource = self.api.root.add_resource("batch")
        batch_resource.add_resource("validate").add_method(
            "POST",
            apigateway.LambdaIntegration(self.batch_upload_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        batch_resource.add_resource("upload").add_method(
            "POST",
            apigateway.LambdaIntegration(self.batch_upload_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # Quiz routes (with authorization)
        quiz_resource = self.api.root.add_resource("quiz")
        
        # POST /quiz/start - Start a new quiz session
        quiz_start = quiz_resource.add_resource("start")
        quiz_start.add_method(
            "POST",
            apigateway.LambdaIntegration(self.quiz_engine_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # POST /quiz/answer - Submit answer for current question
        quiz_answer = quiz_resource.add_resource("answer")
        quiz_answer.add_method(
            "POST",
            apigateway.LambdaIntegration(self.quiz_engine_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # GET /quiz/question - Get next question
        quiz_question = quiz_resource.add_resource("question")
        quiz_question.add_method(
            "GET",
            apigateway.LambdaIntegration(self.quiz_engine_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # POST /quiz/evaluate - Direct answer evaluation (for testing)
        quiz_resource.add_resource("evaluate").add_method(
            "POST",
            apigateway.LambdaIntegration(self.answer_evaluator_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # Progress routes (with authorization)
        progress_resource = self.api.root.add_resource("progress")
        progress_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.progress_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # Add /progress/dashboard endpoint
        dashboard_resource = progress_resource.add_resource("dashboard")
        dashboard_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.progress_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # Create Post-Confirmation Lambda Trigger for Cognito
        # This creates user records in database after successful registration
        self.post_confirmation_lambda = _lambda.Function(
            self,
            "PostConfirmationTrigger",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="post_confirmation.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/cognito_triggers"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
                "AWS_CA_BUNDLE": "/etc/pki/tls/certs/ca-bundle.crt",
                "USER_POOL_ID": self.user_pool.user_pool_id,
            },
            description="Cognito Post-Confirmation trigger - creates user in database"
        )

        # Grant permission to invoke DB Proxy
        self.db_proxy_lambda.grant_invoke(self.post_confirmation_lambda)

        # Grant permission to set custom:status = pending on new users
        self.user_pool.grant(
            self.post_confirmation_lambda,
            "cognito-idp:AdminUpdateUserAttributes",
        )

        # Grant Cognito permission to invoke the Lambda
        self.post_confirmation_lambda.add_permission(
            "CognitoInvoke",
            principal=iam.ServicePrincipal("cognito-idp.amazonaws.com"),
            source_arn=self.user_pool.user_pool_arn
        )

        # Create Pre-Authentication Lambda Trigger for Cognito
        # Blocks login for accounts not yet approved
        self.pre_authentication_lambda = _lambda.Function(
            self,
            "PreAuthenticationTrigger",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="pre_authentication.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/cognito_triggers"),
            timeout=Duration.seconds(10),
            memory_size=128,
            layers=[self.shared_layer],
            environment={
                "AWS_CA_BUNDLE": "/etc/pki/tls/certs/ca-bundle.crt",
            },
            description="Cognito Pre-Authentication trigger - enforces approval gate",
        )
        self.pre_authentication_lambda.add_permission(
            "CognitoInvoke",
            principal=iam.ServicePrincipal("cognito-idp.amazonaws.com"),
            source_arn=self.user_pool.user_pool_arn,
        )

        # Create User Management Lambda (admin approve/deny)
        self.user_management_lambda = _lambda.Function(
            self,
            "UserManagementFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/user_management"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            environment={
                "USER_POOL_ID": self.user_pool.user_pool_id,
                "SES_FROM_EMAIL": "noreply@syntacticallysugary.dev",
                "APP_URL": "https://d3awlgby2429wc.cloudfront.net",
                "AWS_CA_BUNDLE": "/etc/pki/tls/certs/ca-bundle.crt",
            },
            description="Admin user management - list, approve, deny pending registrations",
        )
        self.user_pool.grant(
            self.user_management_lambda,
            "cognito-idp:AdminGetUser",
            "cognito-idp:AdminUpdateUserAttributes",
            "cognito-idp:ListUsers",
        )
        self.user_management_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                resources=["*"],
            )
        )

        # Admin API routes (Cognito-authorized; admin group check enforced inside Lambda)
        admin_resource = self.api.root.add_resource("admin")
        admin_users_resource = admin_resource.add_resource("users")
        admin_users_resource.add_resource("pending").add_method(
            "GET",
            apigateway.LambdaIntegration(self.user_management_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )
        admin_user_resource = admin_users_resource.add_resource("{username}")
        admin_user_resource.add_resource("approve").add_method(
            "POST",
            apigateway.LambdaIntegration(self.user_management_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )
        admin_user_resource.add_resource("deny").add_method(
            "POST",
            apigateway.LambdaIntegration(self.user_management_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
        )

        # Create custom resource to update Cognito User Pool with PostConfirmation trigger
        # This is needed because the User Pool is in a different stack
        update_cognito_role = iam.Role(
            self,
            "UpdateCognitoRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "UpdateCognito": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["cognito-idp:UpdateUserPool", "cognito-idp:DescribeUserPool"],
                            resources=[self.user_pool.user_pool_arn]
                        )
                    ]
                )
            }
        )
        
        update_cognito_lambda = _lambda.Function(
            self,
            "UpdateCognitoTrigger",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=_lambda.Code.from_inline("""
import boto3
import json
import cfnresponse

cognito = boto3.client('cognito-idp')

def handler(event, context):
    try:
        user_pool_id = event['ResourceProperties']['UserPoolId']
        post_confirmation_arn = event['ResourceProperties']['PostConfirmationArn']
        pre_signup_arn = event['ResourceProperties']['PreSignUpArn']
        pre_authentication_arn = event['ResourceProperties']['PreAuthenticationArn']

        if event['RequestType'] in ['Create', 'Update']:
            # Update with all three triggers
            cognito.update_user_pool(
                UserPoolId=user_pool_id,
                LambdaConfig={
                    'PreSignUp': pre_signup_arn,
                    'PostConfirmation': post_confirmation_arn,
                    'PreAuthentication': pre_authentication_arm,
                }
            )
            print(f"Updated User Pool {user_pool_id} with all Cognito triggers")
        
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    except Exception as e:
        print(f"Error: {e}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {})
"""),
            role=update_cognito_role,
            timeout=Duration.seconds(30)
        )
        
        # Create custom resource
        cr.AwsCustomResource(
            self,
            "UpdateUserPoolTrigger",
            on_create=cr.AwsSdkCall(
                service="Lambda",
                action="invoke",
                parameters={
                    "FunctionName": update_cognito_lambda.function_name,
                    "Payload": json.dumps({
                        "RequestType": "Create",
                        "ResourceProperties": {
                            "UserPoolId": self.user_pool.user_pool_id,
                            "PostConfirmationArn": self.post_confirmation_lambda.function_arn,
                            "PreSignUpArn": self.auth_stack.pre_signup_lambda.function_arn,
                            "PreAuthenticationArn": self.pre_authentication_lambda.function_arn,
                        }
                    })
                },
                physical_resource_id=cr.PhysicalResourceId.of("UpdateUserPoolTrigger")
            ),
            on_update=cr.AwsSdkCall(
                service="Lambda",
                action="invoke",
                parameters={
                    "FunctionName": update_cognito_lambda.function_name,
                    "Payload": json.dumps({
                        "RequestType": "Update",
                        "ResourceProperties": {
                            "UserPoolId": self.user_pool.user_pool_id,
                            "PostConfirmationArn": self.post_confirmation_lambda.function_arn,
                            "PreSignUpArn": self.auth_stack.pre_signup_lambda.function_arn,
                            "PreAuthenticationArn": self.pre_authentication_lambda.function_arn,
                        }
                    })
                },
                physical_resource_id=cr.PhysicalResourceId.of("UpdateUserPoolTrigger")
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(
                    actions=["lambda:InvokeFunction"],
                    resources=[update_cognito_lambda.function_arn]
                )
            ])
        )
        
        # CloudFormation Outputs
        CfnOutput(
            self,
            "ApiUrl",
            value=self.api.url,
            description="API Gateway URL",
            export_name=f"{construct_id}-ApiUrl"
        )
        
        CfnOutput(
            self,
            "QuizEngineFunctionName",
            value=self.quiz_engine_lambda.function_name,
            description="Quiz Engine Lambda function name"
        )
        
        CfnOutput(
            self,
            "AnswerEvaluatorFunctionName",
            value=self.answer_evaluator_lambda.function_name,
            description="Answer Evaluator Lambda function name"
        )
        
        CfnOutput(
            self,
            "MigrationRunnerFunctionName",
            value=self.migration_runner_lambda.function_name,
            description="Migration Runner Lambda function name"
        )

"""Auth Stack for Know-It-All Tutor System
Contains Cognito User Pool and Pre-SignUp Lambda trigger
"""

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_cognito as cognito,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as _lambda,
)
from constructs import Construct


class AuthStack(Stack):
    """Authentication infrastructure stack containing Cognito resources.
    This stack changes occasionally.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Cognito User Pool
        self.user_pool = cognito.UserPool(
            self,
            "AuthUserPool",
            user_pool_name="know-it-all-tutor-multistack-dev",  # Different name for testing
            # Users sign in with email, not username
            sign_in_aliases=cognito.SignInAliases(email=True),
            # Password requirements
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            # NO EMAIL VERIFICATION for dev - users are immediately confirmed
            auto_verify=cognito.AutoVerifiedAttrs(),  # Empty = no verification
            # Allow users to sign up themselves
            self_sign_up_enabled=True,
            # Custom attributes for approval workflow
            custom_attributes={
                "status": cognito.StringAttribute(mutable=True, min_len=0, max_len=20),
            },
            # Clean up when stack is deleted (dev environment)
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Create User Pool Client
        self.user_pool_client = cognito.UserPoolClient(
            self,
            "AuthUserPoolClient",
            user_pool=self.user_pool,
            user_pool_client_name="know-it-all-tutor-web-client-multistack-dev",
            # Allow username/password authentication
            auth_flows=cognito.AuthFlow(user_password=True, user_srp=True),
            # Token validity periods
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            # Don't generate a client secret (for web apps)
            generate_secret=False,
        )

        # Create Pre-SignUp Lambda Trigger (auto-confirm + notify admin via SES)
        self.pre_signup_lambda = _lambda.Function(
            self,
            "PreSignUpTrigger",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/cognito_pre_signup"),
            timeout=Duration.seconds(10),
            memory_size=128,
            environment={
                "ADMIN_EMAIL": "huschlej@comcast.net",
                "SES_FROM_EMAIL": "huschlej@comcast.net",
                "APP_URL": "https://d3awlgby2429wc.cloudfront.net",
            },
            description="Cognito Pre-SignUp trigger - auto-confirms users and notifies admin",
        )

        # Allow pre-signup Lambda to send email via SES
        self.pre_signup_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                resources=["*"],
            )
        )

        # Grant Cognito permission to invoke the Lambda
        self.pre_signup_lambda.add_permission(
            "CognitoInvoke",
            principal=iam.ServicePrincipal("cognito-idp.amazonaws.com"),
            source_arn=self.user_pool.user_pool_arn,
        )

        # Add trigger to User Pool
        self.user_pool.add_trigger(cognito.UserPoolOperation.PRE_SIGN_UP, self.pre_signup_lambda)

        # CloudFormation Outputs
        CfnOutput(
            self,
            "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID",
            export_name=f"{construct_id}-UserPoolId",
        )

        CfnOutput(
            self,
            "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
            export_name=f"{construct_id}-UserPoolClientId",
        )

        CfnOutput(
            self,
            "UserPoolArn",
            value=self.user_pool.user_pool_arn,
            description="Cognito User Pool ARN",
            export_name=f"{construct_id}-UserPoolArn",
        )

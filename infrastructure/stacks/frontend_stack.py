"""
Frontend Stack for Know-It-All Tutor System
Contains S3 bucket and CloudFront distribution for static website hosting
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_certificatemanager as acm,
    Duration,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct


class FrontendStack(Stack):
    """
    Frontend infrastructure stack containing S3 and CloudFront.
    This stack changes frequently.
    """
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        backend_stack,
        auth_stack,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Import resources from other stacks
        self.api_url = backend_stack.api.url
        self.user_pool_id = auth_stack.user_pool.user_pool_id
        self.user_pool_client_id = auth_stack.user_pool_client.user_pool_client_id
        
        # Create S3 bucket for static website hosting
        self.frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            website_index_document="index.html",
            website_error_document="index.html",  # SPA routing
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False
            ),
            removal_policy=RemovalPolicy.DESTROY,  # For dev environment
            auto_delete_objects=True  # Clean up on stack deletion
        )
        
        # Optional custom domain — supply both context vars to enable:
        #   cdk deploy -c custom_domain=tutor.syntacticallysugary.dev \
        #              -c certificate_arn=arn:aws:acm:us-east-1:...
        custom_domain: str | None = self.node.try_get_context("custom_domain")
        certificate_arn: str | None = self.node.try_get_context("certificate_arn")

        custom_domain_kwargs = {}
        if custom_domain and certificate_arn:
            custom_domain_kwargs["domain_names"] = [custom_domain]
            custom_domain_kwargs["certificate"] = acm.Certificate.from_certificate_arn(
                self, "CustomDomainCert", certificate_arn
            )

        # Create CloudFront distribution
        self.distribution = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3StaticWebsiteOrigin(self.frontend_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                )
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            comment="Know-It-All Tutor Frontend - Multi-Stack Dev",
            **custom_domain_kwargs
        )
        
        # Deploy frontend build to S3
        # Note: Requires frontend/dist to exist (run npm build first)
        # CloudFront cache invalidation is handled separately in CI via aws cloudfront
        # create-invalidation to avoid CDK bug https://github.com/aws/aws-cdk/issues/15891
        self.frontend_deployment = s3deploy.BucketDeployment(
            self,
            "DeployFrontend",
            sources=[s3deploy.Source.asset("../frontend/dist")],
            destination_bucket=self.frontend_bucket,
        )
        
        # CloudFormation Outputs
        if custom_domain and certificate_arn:
            CfnOutput(
                self,
                "CustomDomainURL",
                value=f"https://{custom_domain}",
                description="Custom domain URL for frontend application",
                export_name=f"{construct_id}-CustomDomainURL"
            )

        CfnOutput(
            self,
            "CloudFrontURL",
            value=f"https://{self.distribution.distribution_domain_name}",
            description="CloudFront URL for frontend application",
            export_name=f"{construct_id}-CloudFrontURL"
        )
        
        CfnOutput(
            self,
            "FrontendBucketName",
            value=self.frontend_bucket.bucket_name,
            description="S3 bucket name for frontend",
            export_name=f"{construct_id}-FrontendBucketName"
        )
        
        CfnOutput(
            self,
            "DistributionId",
            value=self.distribution.distribution_id,
            description="CloudFront distribution ID",
            export_name=f"{construct_id}-DistributionId"
        )
        
        # Output backend config for reference
        CfnOutput(
            self,
            "BackendApiUrl",
            value=self.api_url,
            description="Backend API URL (for frontend config)"
        )
        
        CfnOutput(
            self,
            "CognitoUserPoolId",
            value=self.user_pool_id,
            description="Cognito User Pool ID (for frontend config)"
        )
        
        CfnOutput(
            self,
            "CognitoClientId",
            value=self.user_pool_client_id,
            description="Cognito Client ID (for frontend config)"
        )

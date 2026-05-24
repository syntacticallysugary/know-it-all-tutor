"""
Database Stack for Know-It-All Tutor System
Contains Aurora DSQL cluster (serverless, consumption-based, free-tier eligible)
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_dsql as dsql,
    aws_ssm as ssm,
    CfnOutput,
    RemovalPolicy,
)
from constructs import Construct


class DatabaseStack(Stack):
    """
    Database infrastructure stack using Aurora DSQL.
    No VPC required — DSQL is accessed over HTTPS with IAM auth.
    Free tier: 100K DPUs + 1 GB storage/month.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.cluster = dsql.CfnCluster(
            self,
            "TutorDSQLCluster",
            deletion_protection_enabled=False,  # dev environment
        )

        self.cluster_endpoint = self.cluster.attr_endpoint
        self.cluster_arn = self.cluster.attr_resource_arn

        # Publish endpoint to SSM so BackendStack can resolve it without
        # a CloudFormation Fn::ImportValue dependency (avoids export locks
        # if the database layer ever needs to change again).
        ssm.StringParameter(
            self,
            "DSQLEndpointParam",
            parameter_name="/tutor-system/dev/dsql-endpoint",
            string_value=self.cluster_endpoint,
            description="Aurora DSQL cluster endpoint",
        )

        CfnOutput(
            self,
            "DSQLEndpoint",
            value=self.cluster_endpoint,
            description="Aurora DSQL cluster endpoint",
            export_name=f"{construct_id}-DSQLEndpoint",
        )

        CfnOutput(
            self,
            "DSQLClusterArn",
            value=self.cluster_arn,
            description="Aurora DSQL cluster ARN",
            export_name=f"{construct_id}-DSQLClusterArn",
        )

        # ── Expand-Contract migration placeholder ──────────────────────────
        # CloudFormation diffs by logical ID, not construct ID. CDK's uniqueness
        # algorithm can produce a logical ID that differs from the construct ID,
        # so we use override_logical_id() to force the exact string into the
        # synthesized template. This makes CloudFormation see an in-place value
        # update instead of delete-old + add-new — which would be blocked while
        # BackendStack still imports the export.
        # Remove after Phase 1 deploys and BackendStack stops importing this export.
        _legacy_endpoint_id = "ExportsOutputFnGetAttTutorDatabaseC3C89480EndpointAddressB4536218"
        _endpoint_placeholder = CfnOutput(
            self,
            "LegacyRDSEndpointPlaceholder",
            value=self.cluster_endpoint,
            export_name=_legacy_endpoint_id,
        )
        _endpoint_placeholder.override_logical_id(_legacy_endpoint_id)

        # Second auto-generated export: BackendStack imported the DB credentials
        # secret ARN via Ref. DSQL uses IAM auth — no credentials secret exists —
        # so we export a sentinel string. BackendStack's new template does not
        # reference this export; the Fn::ImportValue disappears after BackendStack
        # redeploys. Remove this placeholder in Phase 2 alongside the one above.
        _legacy_creds_id = "ExportsOutputRefDBCredentialsCBF39AE96FE42413"
        _creds_placeholder = CfnOutput(
            self,
            "LegacyDBCredentialsPlaceholder",
            value="MIGRATED-TO-DSQL-IAM-AUTH",
            export_name=_legacy_creds_id,
        )
        _creds_placeholder.override_logical_id(_legacy_creds_id)

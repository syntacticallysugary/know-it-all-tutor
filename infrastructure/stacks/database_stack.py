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
        # The construct ID must match the old CDK-auto-generated logical ID exactly.
        # CloudFormation computes diffs by logical ID: if the logical ID changes,
        # it treats this as delete-old + add-new, and the delete is blocked while
        # BackendStack still imports the export. Matching the logical ID makes
        # CloudFormation see it as an in-place value update — no removal, no lock.
        # Remove after Phase 1 deploys and BackendStack stops importing this export.
        CfnOutput(
            self,
            "ExportsOutputFnGetAttTutorDatabaseC3C89480EndpointAddressB4536218",
            value=self.cluster_endpoint,
            export_name="ExportsOutputFnGetAttTutorDatabaseC3C89480EndpointAddressB4536218",
        )

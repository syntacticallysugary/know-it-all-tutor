"""
Database Stack for Know-It-All Tutor System
Contains Aurora DSQL cluster (serverless, consumption-based, free-tier eligible)
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_dsql as dsql,
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

        # Expose endpoint and ARN for BackendStack
        self.cluster_endpoint = self.cluster.attr_endpoint
        self.cluster_arn = self.cluster.attr_resource_arn

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

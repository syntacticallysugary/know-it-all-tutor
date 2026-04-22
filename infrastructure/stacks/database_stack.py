"""
Database Stack for Know-It-All Tutor System
Contains RDS PostgreSQL instance and Secrets Manager secret
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    Duration,
    RemovalPolicy,
    CfnOutput,
    Fn
)
from constructs import Construct


class DatabaseStack(Stack):
    """
    Database infrastructure stack containing RDS and credentials.
    This stack rarely changes.
    """
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        network_stack,  # Dependency on Network Stack
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Use VPC directly from Network Stack (same deployment)
        self.vpc = network_stack.vpc
        self.rds_security_group = network_stack.rds_security_group
        
        # Create database credentials in Secrets Manager
        self.db_credentials = secretsmanager.Secret(
            self,
            "DBCredentials",
            secret_name="tutor-system/db-credentials-multistack-dev",  # Different name to avoid conflict
            description="RDS PostgreSQL credentials for tutor system",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username":"tutor_admin"}',
                generate_string_key="password",
                exclude_characters="\"@/\\ '",
                password_length=32
            ),
            removal_policy=RemovalPolicy.DESTROY  # Dev only - delete with stack
        )
        
        # Create RDS PostgreSQL (Free Tier - t4g.micro)
        self.database = rds.DatabaseInstance(
            self,
            "TutorDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_11
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON,  # t4g
                ec2.InstanceSize.MICRO  # Free tier eligible
            ),
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[self.rds_security_group],
            credentials=rds.Credentials.from_secret(self.db_credentials),
            database_name="tutor_system",
            allocated_storage=20,  # Free tier: 20GB
            max_allocated_storage=20,  # Disable autoscaling to stay in free tier
            storage_encrypted=True,  # Always encrypt
            backup_retention=Duration.days(7),  # Free tier: 7 days
            deletion_protection=False,  # Dev environment
            removal_policy=RemovalPolicy.DESTROY,  # Dev only
            publicly_accessible=False,  # Security best practice
            multi_az=False,  # Single AZ for free tier
        )
        
        # CloudFormation Outputs
        CfnOutput(
            self,
            "DatabaseEndpoint",
            value=self.database.db_instance_endpoint_address,
            description="RDS PostgreSQL endpoint",
            export_name=f"{construct_id}-DatabaseEndpoint"
        )
        
        CfnOutput(
            self,
            "DatabaseSecretArn",
            value=self.db_credentials.secret_arn,
            description="ARN of database credentials secret",
            export_name=f"{construct_id}-DatabaseSecretArn"
        )
        
        CfnOutput(
            self,
            "DatabaseName",
            value="tutor_system",
            description="Database name",
            export_name=f"{construct_id}-DatabaseName"
        )

#!/usr/bin/env python3
"""
Multi-Stack CDK App for Know-It-All Tutor System

This app orchestrates 6 separate stacks with clear separation of concerns:
- NetworkStack: VPC, security groups, endpoints
- DatabaseStack: RDS PostgreSQL, Secrets Manager
- AuthStack: Cognito User Pool, Pre-SignUp Lambda
- BackendStack: Lambda functions, API Gateway
- FrontendStack: S3, CloudFront
- MonitoringStack: CloudWatch dashboards, alarms, budgets
"""
import aws_cdk as cdk
from stacks.network_stack import NetworkStack
from stacks.database_stack import DatabaseStack
from stacks.auth_stack import AuthStack
from stacks.backend_stack import BackendStack
from stacks.frontend_stack import FrontendStack
from stacks.monitoring_stack import SimpleMonitoringStack

app = cdk.App()

# Environment configuration
env_config = cdk.Environment(
    account="257949588978",
    region="us-east-1"
)

# Get optional configuration from context
notification_email = app.node.try_get_context("notification_email")
monthly_budget = app.node.try_get_context("monthly_budget") or 10.0

# 1. Network Stack (foundation - no dependencies)
network_stack = NetworkStack(
    app,
    "NetworkStack-dev",
    env=env_config,
    description="Network infrastructure for Tutor System - Dev"
)

# 2. Database Stack (no VPC dependency — DSQL is serverless)
database_stack = DatabaseStack(
    app,
    "DatabaseStack-dev",
    env=env_config,
    description="Database infrastructure for Tutor System - Dev"
)

# 3. Auth Stack (independent)
auth_stack = AuthStack(
    app,
    "AuthStack-dev",
    env=env_config,
    description="Authentication infrastructure for Tutor System - Dev"
)

# 4. Backend Stack (depends on Database, Auth)
# database_stack is not passed directly — DSQL endpoint is resolved via SSM
# to avoid a CloudFormation Fn::ImportValue dependency. Deploy order is
# enforced by add_dependency() below.
backend_stack = BackendStack(
    app,
    "BackendStack-dev",
    auth_stack=auth_stack,
    env=env_config,
    description="Backend infrastructure for Tutor System - Dev"
)
backend_stack.add_dependency(network_stack)
backend_stack.add_dependency(database_stack)
backend_stack.add_dependency(auth_stack)

# 5. Frontend Stack (depends on Backend, Auth)
frontend_stack = FrontendStack(
    app,
    "FrontendStack-dev",
    backend_stack=backend_stack,
    auth_stack=auth_stack,
    env=env_config,
    description="Frontend infrastructure for Tutor System - Dev"
)
frontend_stack.add_dependency(backend_stack)
frontend_stack.add_dependency(auth_stack)

# 6. Monitoring Stack (depends on Backend, Frontend)
monitoring_stack = SimpleMonitoringStack(
    app,
    "MonitoringStack-dev",
    backend_stack=backend_stack,
    frontend_stack=frontend_stack,
    env_name="dev",
    notification_email=notification_email,
    monthly_budget_limit=monthly_budget,
    env=env_config,
    description="Monitoring infrastructure for Tutor System - Dev"
)
monitoring_stack.add_dependency(backend_stack)
monitoring_stack.add_dependency(frontend_stack)

app.synth()

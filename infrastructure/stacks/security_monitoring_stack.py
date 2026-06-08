"""
Security Monitoring Stack for Know-It-All Tutor System
Implements AWS CloudTrail, GuardDuty, Config, and CloudWatch security monitoring
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_cloudtrail as cloudtrail,
    aws_guardduty as guardduty,
    aws_config as config,
    aws_cloudwatch as cloudwatch,
    aws_logs as logs,
    aws_s3 as s3,
    aws_iam as iam,
    aws_sns as sns,
    aws_events as events,
    aws_events_targets as targets,
    Duration,
    RemovalPolicy
)
from constructs import Construct
from typing import List, Dict, Any


class SecurityMonitoringStack(Stack):
    """Stack for comprehensive AWS security monitoring and compliance"""
    
    def __init__(self, scope: Construct, construct_id: str, environment: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.environment = environment
        
        # Create S3 bucket for CloudTrail logs
        self.cloudtrail_bucket = self._create_cloudtrail_bucket()
        
        # Create CloudTrail for API call logging
        self.cloudtrail = self._create_cloudtrail()
        
        # Create GuardDuty for threat detection
        self.guardduty_detector = self._create_guardduty()
        
        # Create Config for compliance monitoring
        self.config_recorder = self._create_config_service()
        
        # Create SNS topics for security alerts
        self.security_alerts_topic = self._create_security_alerts_topic()
        
        # Create CloudWatch alarms and metrics
        self.security_alarms = self._create_security_alarms()
        
        # Create EventBridge rules for security events
        self.security_event_rules = self._create_security_event_rules()
        
        # Create outputs
        self._create_outputs()
    
    def _create_cloudtrail_bucket(self) -> s3.Bucket:
        """Create S3 bucket for CloudTrail logs with proper security configuration"""
        bucket = s3.Bucket(
            self,
            "CloudTrailLogsBucket",
            bucket_name=f"tutor-system-cloudtrail-{self.environment}-{self.account}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,  # Always retain security logs
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="CloudTrailLogRetention",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.DEEP_ARCHIVE,
                            transition_after=Duration.days(365)
                        )
                    ],
                    expiration=Duration.days(2555)  # 7 years retention for compliance
                )
            ]
        )
        
        # Add bucket policy for CloudTrail
        bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AWSCloudTrailAclCheck",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudtrail.amazonaws.com")],
                actions=["s3:GetBucketAcl"],
                resources=[bucket.bucket_arn]
            )
        )
        
        bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AWSCloudTrailWrite",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudtrail.amazonaws.com")],
                actions=["s3:PutObject"],
                resources=[f"{bucket.bucket_arn}/*"],
                conditions={
                    "StringEquals": {
                        "s3:x-amz-acl": "bucket-owner-full-control"
                    }
                }
            )
        )
        
        return bucket
    
    def _create_cloudtrail(self) -> cloudtrail.Trail:
        """Create CloudTrail for comprehensive API call logging"""
        # Create CloudWatch log group for CloudTrail
        log_group = logs.LogGroup(
            self,
            "CloudTrailLogGroup",
            log_group_name=f"/aws/cloudtrail/tutor-system-{self.environment}",
            retention=logs.RetentionDays.ONE_YEAR,
            removal_policy=RemovalPolicy.RETAIN
        )
        
        # Create CloudTrail
        trail = cloudtrail.Trail(
            self,
            "SecurityCloudTrail",
            trail_name=f"tutor-system-security-trail-{self.environment}",
            bucket=self.cloudtrail_bucket,
            s3_key_prefix="cloudtrail-logs",
            include_global_service_events=True,
            is_multi_region_trail=True,
            enable_file_validation=True,
            send_to_cloud_watch_logs=True,
            cloud_watch_logs_group=log_group,
            management_events=cloudtrail.ReadWriteType.ALL,

            s3_bucket_events=[
                cloudtrail.S3EventSelector(
                    bucket=self.cloudtrail_bucket,
                    object_prefix="",
                    include_management_events=True,
                    read_write_type=cloudtrail.ReadWriteType.ALL
                )
            ]
        )

        trail.add_lambda_event_selector(
            include_management_events=True,
            read_write_type=cloudtrail.ReadWriteType.ALL
        )

        self.cloudtrail_log_group = log_group
        return trail
    
    def _create_guardduty(self) -> guardduty.CfnDetector:
        """Create GuardDuty detector for threat detection"""
        detector = guardduty.CfnDetector(
            self,
            "GuardDutyDetector",
            enable=True,
            finding_publishing_frequency="FIFTEEN_MINUTES",
            datasources=guardduty.CfnDetector.CFNDataSourceConfigurationsProperty(
                s3_logs=guardduty.CfnDetector.CFNS3LogsConfigurationProperty(
                    enable=True
                ),
                kubernetes=guardduty.CfnDetector.CFNKubernetesConfigurationProperty(
                    audit_logs=guardduty.CfnDetector.CFNKubernetesAuditLogsConfigurationProperty(
                        enable=False  # Not using EKS in this project
                    )
                ),
                malware_protection=guardduty.CfnDetector.CFNMalwareProtectionConfigurationProperty(
                    scan_ec2_instance_with_findings=guardduty.CfnDetector.CFNScanEc2InstanceWithFindingsConfigurationProperty(
                        ebs_volumes=False  # Not using EC2 in this project
                    )
                )
            )
        )
        
        return detector
    
    def _create_config_service(self) -> config.CfnConfigurationRecorder:
        """Create AWS Config for compliance monitoring"""
        # Create S3 bucket for Config
        config_bucket = s3.Bucket(
            self,
            "ConfigBucket",
            bucket_name=f"tutor-system-config-{self.environment}-{self.account}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ConfigLogRetention",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        )
                    ],
                    expiration=Duration.days(365)
                )
            ]
        )
        
        # Create IAM role for Config
        config_role = iam.Role(
            self,
            "ConfigRole",
            assumed_by=iam.ServicePrincipal("config.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/ConfigRole")
            ]
        )
        
        # Grant Config permissions to write to S3
        config_bucket.grant_read_write(config_role)
        
        # Create delivery channel
        delivery_channel = config.CfnDeliveryChannel(
            self,
            "ConfigDeliveryChannel",
            s3_bucket_name=config_bucket.bucket_name,
            config_snapshot_delivery_properties=config.CfnDeliveryChannel.ConfigSnapshotDeliveryPropertiesProperty(
                delivery_frequency="TwentyFour_Hours"
            )
        )
        
        # Create configuration recorder
        recorder = config.CfnConfigurationRecorder(
            self,
            "ConfigRecorder",
            role_arn=config_role.role_arn,
            recording_group=config.CfnConfigurationRecorder.RecordingGroupProperty(
                all_supported=True,
                include_global_resource_types=True,
                resource_types=[]
            )
        )
        
        # Create Config rules for security compliance
        self._create_config_rules()
        
        return recorder
    
    def _create_config_rules(self):
        """Create AWS Config rules for security compliance monitoring"""
        # Rule: Root access key check
        config.CfnConfigRule(
            self,
            "RootAccessKeyCheck",
            config_rule_name="root-access-key-check",
            source=config.CfnConfigRule.SourceProperty(
                owner="AWS",
                source_identifier="ROOT_ACCESS_KEY_CHECK"
            )
        )
        
        # Rule: IAM password policy
        config.CfnConfigRule(
            self,
            "IAMPasswordPolicy",
            config_rule_name="iam-password-policy",
            source=config.CfnConfigRule.SourceProperty(
                owner="AWS",
                source_identifier="IAM_PASSWORD_POLICY"
            )
        )
        
        # Rule: S3 bucket public access prohibited
        config.CfnConfigRule(
            self,
            "S3BucketPublicAccessProhibited",
            config_rule_name="s3-bucket-public-access-prohibited",
            source=config.CfnConfigRule.SourceProperty(
                owner="AWS",
                source_identifier="S3_BUCKET_PUBLIC_ACCESS_PROHIBITED"
            )
        )
        
        # Rule: Lambda function public access prohibited
        config.CfnConfigRule(
            self,
            "LambdaFunctionPublicAccessProhibited",
            config_rule_name="lambda-function-public-access-prohibited",
            source=config.CfnConfigRule.SourceProperty(
                owner="AWS",
                source_identifier="LAMBDA_FUNCTION_PUBLIC_ACCESS_PROHIBITED"
            )
        )
        
        # Rule: RDS instance public access check
        config.CfnConfigRule(
            self,
            "RDSInstancePublicAccessCheck",
            config_rule_name="rds-instance-public-access-check",
            source=config.CfnConfigRule.SourceProperty(
                owner="AWS",
                source_identifier="RDS_INSTANCE_PUBLIC_ACCESS_CHECK"
            )
        )
        
        # Rule: CloudTrail enabled
        config.CfnConfigRule(
            self,
            "CloudTrailEnabled",
            config_rule_name="cloudtrail-enabled",
            source=config.CfnConfigRule.SourceProperty(
                owner="AWS",
                source_identifier="CLOUD_TRAIL_ENABLED"
            )
        )
    
    def _create_security_alerts_topic(self) -> sns.Topic:
        """Create SNS topic for security alerts"""
        topic = sns.Topic(
            self,
            "SecurityAlertsTopic",
            topic_name=f"tutor-system-security-alerts-{self.environment}",
            display_name="Security Alerts for Know-It-All Tutor System"
        )
        
        topic.add_subscription(
            sns.Subscription(
                topic=topic,
                endpoint="knowitall-tutor@syntacticallysugary.dev",
                protocol=sns.SubscriptionProtocol.EMAIL
            )
        )
        
        return topic
    
    def _create_security_alarms(self) -> List[cloudwatch.Alarm]:
        """Create CloudWatch alarms for security monitoring"""
        alarms = []
        
        # Alarm for root account usage — uses a metric filter on the CloudTrail log
        # group so it only fires on actual root API calls, not all log events.
        root_metric_filter = logs.MetricFilter(
            self,
            "RootUsageMetricFilter",
            log_group=self.cloudtrail_log_group,
            metric_namespace="TutorSystem/Security",
            metric_name="RootAccountUsage",
            filter_pattern=logs.FilterPattern.literal(
                '{ $.userIdentity.type = "Root" && $.userIdentity.invokedBy NOT EXISTS && $.eventType != "AwsServiceEvent" }'
            ),
            metric_value="1",
            default_value=0,
        )
        root_usage_alarm = cloudwatch.Alarm(
            self,
            "RootAccountUsageAlarm",
            alarm_name=f"tutor-system-root-usage-{self.environment}",
            alarm_description="Alert when root account is used",
            metric=root_metric_filter.metric(statistic="Sum"),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        )
        root_usage_alarm.add_alarm_action(
            cloudwatch.SnsAction(self.security_alerts_topic)
        )
        alarms.append(root_usage_alarm)
        
        # Alarm for failed login attempts
        failed_login_alarm = cloudwatch.Alarm(
            self,
            "FailedLoginAttemptsAlarm",
            alarm_name=f"tutor-system-failed-logins-{self.environment}",
            alarm_description="Alert on multiple failed login attempts",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="4XXError",
                dimensions_map={
                    "ApiName": f"tutor-system-api-{self.environment}"
                },
                statistic="Sum"
            ),
            threshold=10,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
        )
        failed_login_alarm.add_alarm_action(
            cloudwatch.SnsAction(self.security_alerts_topic)
        )
        alarms.append(failed_login_alarm)
        
        # Alarm for Lambda function errors
        lambda_error_alarm = cloudwatch.Alarm(
            self,
            "LambdaErrorAlarm",
            alarm_name=f"tutor-system-lambda-errors-{self.environment}",
            alarm_description="Alert on Lambda function errors",
            metric=cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                statistic="Sum"
            ),
            threshold=5,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
        )
        lambda_error_alarm.add_alarm_action(
            cloudwatch.SnsAction(self.security_alerts_topic)
        )
        alarms.append(lambda_error_alarm)
        
        # Alarm for unusual API Gateway traffic
        api_traffic_alarm = cloudwatch.Alarm(
            self,
            "UnusualAPITrafficAlarm",
            alarm_name=f"tutor-system-unusual-traffic-{self.environment}",
            alarm_description="Alert on unusual API Gateway traffic patterns",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="Count",
                dimensions_map={
                    "ApiName": f"tutor-system-api-{self.environment}"
                },
                statistic="Sum"
            ),
            threshold=1000,  # Adjust based on expected traffic
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
        )
        api_traffic_alarm.add_alarm_action(
            cloudwatch.SnsAction(self.security_alerts_topic)
        )
        alarms.append(api_traffic_alarm)
        
        return alarms
    
    def _create_security_event_rules(self) -> List[events.Rule]:
        """Create EventBridge rules for security event monitoring"""
        rules = []
        
        # Rule for GuardDuty findings
        guardduty_rule = events.Rule(
            self,
            "GuardDutyFindingsRule",
            rule_name=f"tutor-system-guardduty-findings-{self.environment}",
            description="Route GuardDuty findings to SNS",
            event_pattern=events.EventPattern(
                source=["aws.guardduty"],
                detail_type=["GuardDuty Finding"],
                detail={
                    "severity": [7.0, 8.0, 8.5, 9.0]  # High and critical severity only
                }
            )
        )
        guardduty_rule.add_target(
            targets.SnsTopic(self.security_alerts_topic)
        )
        rules.append(guardduty_rule)
        
        # Rule for Config compliance changes
        config_rule = events.Rule(
            self,
            "ConfigComplianceRule",
            rule_name=f"tutor-system-config-compliance-{self.environment}",
            description="Route Config compliance changes to SNS",
            event_pattern=events.EventPattern(
                source=["aws.config"],
                detail_type=["Config Rules Compliance Change"],
                detail={
                    "newEvaluationResult": {
                        "complianceType": ["NON_COMPLIANT"]
                    }
                }
            )
        )
        config_rule.add_target(
            targets.SnsTopic(self.security_alerts_topic)
        )
        rules.append(config_rule)
        
        # Rule for CloudTrail API calls of interest
        cloudtrail_rule = events.Rule(
            self,
            "CloudTrailSecurityEventsRule",
            rule_name=f"tutor-system-cloudtrail-security-{self.environment}",
            description="Route security-relevant CloudTrail events to SNS",
            event_pattern=events.EventPattern(
                source=["aws.cloudtrail"],
                detail={
                    "eventName": [
                        "CreateUser",
                        "DeleteUser",
                        "AttachUserPolicy",
                        "DetachUserPolicy",
                        "CreateRole",
                        "DeleteRole",
                        "PutBucketPolicy",
                        "DeleteBucketPolicy",
                        "CreateAccessKey",
                        "DeleteAccessKey"
                    ]
                }
            )
        )
        cloudtrail_rule.add_target(
            targets.SnsTopic(self.security_alerts_topic)
        )
        rules.append(cloudtrail_rule)
        
        return rules
    
    def _create_outputs(self):
        """Create CloudFormation outputs for security monitoring resources"""
        cdk.CfnOutput(
            self,
            "CloudTrailArn",
            value=self.cloudtrail.trail_arn,
            description="CloudTrail ARN for API logging"
        )
        
        cdk.CfnOutput(
            self,
            "GuardDutyDetectorId",
            value=self.guardduty_detector.ref,
            description="GuardDuty detector ID"
        )
        
        cdk.CfnOutput(
            self,
            "SecurityAlertsTopicArn",
            value=self.security_alerts_topic.topic_arn,
            description="SNS topic ARN for security alerts"
        )
        
        cdk.CfnOutput(
            self,
            "CloudTrailBucketName",
            value=self.cloudtrail_bucket.bucket_name,
            description="S3 bucket name for CloudTrail logs"
        )
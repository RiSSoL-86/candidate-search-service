import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_lambda_event_sources as sources
from aws_cdk import aws_rds as rds
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from stacks.config import Config
from stacks.constructs.database.instance import DatabaseInstanceConstruct
from stacks.constructs.database.settings import DatabaseSettingsConstruct
from stacks.constructs.layers import LayersConstruct


class DatabaseIngestStack(cdk.Stack):
    """Lambda that writes one resume JSON into the candidates database."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: Config,
        description: str,
    ) -> None:
        super().__init__(
            scope=scope,
            id=construct_id,
            description=description,
        )

        # Database settings
        settings = DatabaseSettingsConstruct(
            scope=self,
            construct_id="DatabaseSettings",
            config=config,
        )

        # Database instance
        instance = DatabaseInstanceConstruct(
            scope=self,
            construct_id="DatabaseInstance",
            config=config,
        )

        # Layers
        layers = LayersConstruct(
            scope=self,
            construct_id="Layers",
            config=config,
        )

        # Virtual Private Cloud
        vpc = ec2.Vpc.from_vpc_attributes(
            scope=self,
            id="CandidateSearchService-database-vpc",
            vpc_id=instance.vpc_id,
            availability_zones=cdk.Fn.get_azs(),
            isolated_subnet_ids=cdk.Fn.split(
                delimiter=",",
                source=instance.subnet_ids,
                assumed_length=2,
            ),
        )

        # Security Group
        security_group = ec2.SecurityGroup.from_security_group_id(
            scope=self,
            id="CandidateSearchService-database-security-group",
            security_group_id=instance.security_group_id,
        )

        # Database instance
        database = rds.DatabaseInstance.from_database_instance_attributes(
            scope=self,
            id="CandidateSearchService-database-instance",
            instance_identifier=f"{config.resource_prefix}-database",
            instance_endpoint_address=instance.endpoint,
            instance_resource_id=instance.resource_id,
            port=settings.port,
            security_groups=[security_group],
        )

        # Queue for the resumes waiting to be written
        failed = sqs.Queue(
            scope=self,
            id="CandidateSearchService-database-ingest-dead-letter-queue",
            queue_name=f"{config.resource_prefix}-ingest-dead-letter",
            retention_period=cdk.Duration.days(amount=14),
            enforce_ssl=True,
        )

        queue = sqs.Queue(
            scope=self,
            id="CandidateSearchService-database-ingest-queue",
            queue_name=f"{config.resource_prefix}-ingest",
            # Six times the Lambda timeout, as the event source expects.
            visibility_timeout=cdk.Duration.seconds(amount=180),
            retention_period=cdk.Duration.days(amount=4),
            enforce_ssl=True,
            dead_letter_queue=sqs.DeadLetterQueue(
                queue=failed,
                max_receive_count=3,
            ),
        )

        ssm.StringParameter(
            scope=self,
            id="CandidateSearchService-database-ingest-queue-url",
            parameter_name=f"{config.database_prefix}/ingest/queue-url",
            string_value=queue.queue_url,
        )

        # Database ingest Lambda
        ingest = lambda_.Function(
            scope=self,
            id="CandidateSearchService-database-ingest",
            function_name=f"{config.resource_prefix}-database-ingest",
            description="Writes one resume JSON into the candidates database",
            runtime=lambda_.Runtime.PYTHON_3_14,
            architecture=lambda_.Architecture.X86_64,
            code=lambda_.Code.from_asset(
                path="../services/ingest",
                exclude=[
                    ".venv",
                    "__pycache__",
                    "*.pyc",
                    "*.egg-info",
                    ".ruff_cache",
                    ".mypy_cache",
                    ".pytest_cache",
                    "tests",
                ],
            ),
            handler="handler.handler",
            layers=[layers.common, layers.models],
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            environment={
                "DB_HOST": instance.endpoint,
                "DB_PORT": cdk.Token.as_string(value=settings.port),
                "DB_NAME": settings.name,
                "DB_USER": settings.ingest_user,
                "POWERTOOLS_SERVICE_NAME": "ingest",
                "POWERTOOLS_TRACE_DISABLED": "true",
            },
            timeout=cdk.Duration.seconds(amount=30),
            memory_size=512,
            reserved_concurrent_executions=10,
        )

        ingest.add_event_source(
            source=sources.SqsEventSource(
                queue=queue,
                batch_size=10,
                report_batch_item_failures=True,
            )
        )

        database.connections.allow_default_port_from(
            other=ingest,
            description="Database ingest Lambda",
        )
        database.grant_connect(
            grantee=ingest,
            db_user=settings.ingest_user,
        )

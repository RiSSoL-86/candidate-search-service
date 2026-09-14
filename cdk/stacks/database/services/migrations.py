import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_rds as rds
from constructs import Construct

from stacks.config import Config
from stacks.constructs.database.instance import DatabaseInstanceConstruct
from stacks.constructs.database.settings import DatabaseSettingsConstruct
from stacks.constructs.layers import LayersConstruct


class DatabaseMigrationsStack(cdk.Stack):
    """Lambda that runs Alembic against the candidates database."""

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
            id="CandidateSearchService-vpc",
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
            id="CandidateSearchService-database-sg",
            security_group_id=instance.security_group_id,
        )

        # PostgresDatabase
        database = rds.DatabaseInstance.from_database_instance_attributes(
            scope=self,
            id="CandidateSearchService-postgres",
            instance_identifier=f"{config.resource_prefix}-postgres",
            instance_endpoint_address=instance.endpoint,
            instance_resource_id=instance.resource_id,
            port=settings.port,
            security_groups=[security_group],
        )

        # Database migrations Lambda
        migrations = lambda_.Function(
            scope=self,
            id="CandidateSearchService-database-migrations",
            function_name=f"{config.resource_prefix}-database-migrations",
            description="Runs Alembic against the candidates database",
            runtime=lambda_.Runtime.PYTHON_3_14,
            architecture=lambda_.Architecture.X86_64,
            code=lambda_.Code.from_asset(
                path="../services/migrations",
                exclude=[
                    ".venv",
                    "__pycache__",
                    "*.pyc",
                    "*.egg-info",
                    "pyproject.toml",
                ],
            ),
            handler="handler.handler",
            layers=[layers.common],
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            environment={
                "DB_HOST": instance.endpoint,
                "DB_PORT": cdk.Token.as_string(value=settings.port),
                "DB_NAME": settings.name,
                "DB_USER": settings.user,
            },
            timeout=cdk.Duration.minutes(amount=5),
            memory_size=512,
        )

        database.connections.allow_default_port_from(
            other=migrations,
            description="Database migrations Lambda",
        )
        database.grant_connect(
            grantee=migrations,
            db_user=settings.user,
        )

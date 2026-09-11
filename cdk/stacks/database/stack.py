import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_rds as rds
from constructs import Construct

from stacks.config import Config
from stacks.constructs.database import DatabaseConstruct


class DatabaseStack(cdk.Stack):
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

        credentials_secret_name = f"{config.database_prefix}/secret"

        # Database env
        database = DatabaseConstruct(
            scope=self,
            construct_id="Database",
            config=config,
        )

        # Virtual Private Cloud
        vpc = ec2.Vpc(
            scope=self,
            id="CandidateSearchService-vpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        security_group = ec2.SecurityGroup(
            scope=self,
            id="CandidateSearchService-database-sg",
            vpc=vpc,
            description="Access to the candidates Postgres instance",
            allow_all_outbound=False,
        )

        # PostgresDatabase
        self.database = rds.DatabaseInstance(
            scope=self,
            id="CandidateSearchService-postgres",
            instance_identifier=f"{config.resource_prefix}-postgres",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_17
            ),
            instance_type=ec2.InstanceType.of(
                instance_class=ec2.InstanceClass.BURSTABLE4_GRAVITON,
                instance_size=ec2.InstanceSize.MICRO,
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[security_group],
            publicly_accessible=False,
            credentials=rds.Credentials.from_generated_secret(
                username=database.user,
                secret_name=credentials_secret_name,
            ),
            database_name=database.name,
            port=database.port,
            iam_authentication=True,
            allocated_storage=20,
            max_allocated_storage=100,
            storage_type=rds.StorageType.GP3,
            storage_encrypted=True,
            multi_az=False,
            backup_retention=cdk.Duration.days(amount=7),
            deletion_protection=True,
            removal_policy=cdk.RemovalPolicy.SNAPSHOT,
        )

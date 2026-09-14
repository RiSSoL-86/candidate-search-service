import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_rds as rds
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from stacks.config import Config
from stacks.constructs.database.settings import DatabaseSettingsConstruct


class DatabaseInstanceStack(cdk.Stack):
    """Creates the VPC, the security group and the Postgres instance."""

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

        # Database settings
        settings = DatabaseSettingsConstruct(
            scope=self,
            construct_id="DatabaseSettings",
            config=config,
        )

        # Virtual Private Cloud
        vpc = ec2.Vpc(
            scope=self,
            id="CandidateSearchService-database-vpc",
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

        ssm.StringParameter(
            scope=self,
            id="CandidateSearchService-database-vpc-id",
            parameter_name=f"{config.database_prefix}/vpc/id",
            string_value=vpc.vpc_id,
        )

        ssm.StringParameter(
            scope=self,
            id="CandidateSearchService-database-isolated-subnet-ids",
            parameter_name=f"{config.database_prefix}/vpc/isolated-subnet-ids",
            string_value=cdk.Fn.join(
                delimiter=",",
                list_of_values=vpc.select_subnets(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                ).subnet_ids,
            ),
        )

        # Security Group
        security_group = ec2.SecurityGroup(
            scope=self,
            id="CandidateSearchService-database-security-group",
            vpc=vpc,
            description="Access to the candidates Postgres instance",
            allow_all_outbound=False,
        )

        ssm.StringParameter(
            scope=self,
            id="CandidateSearchService-database-security-group-id",
            parameter_name=f"{config.database_prefix}/security-group/id",
            string_value=security_group.security_group_id,
        )

        # Database instance
        self.database = rds.DatabaseInstance(
            scope=self,
            id="CandidateSearchService-database-instance",
            instance_identifier=f"{config.resource_prefix}-database",
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
                username=settings.user,
                secret_name=credentials_secret_name,
            ),
            database_name=settings.name,
            port=settings.port,
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

        ssm.StringParameter(
            scope=self,
            id="CandidateSearchService-database-instance-endpoint",
            parameter_name=f"{config.database_prefix}/instance/endpoint",
            string_value=self.database.db_instance_endpoint_address,
        )

        ssm.StringParameter(
            scope=self,
            id="CandidateSearchService-database-instance-resource-id",
            parameter_name=f"{config.database_prefix}/instance/resource-id",
            string_value=cdk.Token.as_string(
                value=self.database.instance_resource_id
            ),
        )

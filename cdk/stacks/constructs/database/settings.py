import aws_cdk as cdk
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from stacks.config import Config


class DatabaseSettingsConstruct(Construct):
    """Database name, users and port put into SSM by hand before deploy."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: Config,
    ) -> None:
        super().__init__(scope=scope, id=construct_id)

        self.name = ssm.StringParameter.value_for_string_parameter(
            scope=self,
            parameter_name=f"{config.database_prefix}/name",
        )
        self.user = ssm.StringParameter.value_for_string_parameter(
            scope=self,
            parameter_name=f"{config.database_prefix}/user",
        )
        self.migrations_user = ssm.StringParameter.value_for_string_parameter(
            scope=self,
            parameter_name=f"{config.database_prefix}/migrations-user",
        )
        self.ingest_user = ssm.StringParameter.value_for_string_parameter(
            scope=self,
            parameter_name=f"{config.database_prefix}/ingest-user",
        )
        self.port = cdk.Token.as_number(
            value=ssm.StringParameter.value_for_string_parameter(
                scope=self,
                parameter_name=f"{config.database_prefix}/port",
            )
        )

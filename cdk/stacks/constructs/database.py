import aws_cdk as cdk
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from stacks.config import Config


class DatabaseConstruct(Construct):
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
        self.port = cdk.Token.as_number(
            value=ssm.StringParameter.value_for_string_parameter(
                scope=self,
                parameter_name=f"{config.database_prefix}/port",
            )
        )

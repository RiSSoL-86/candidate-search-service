from aws_cdk import aws_ssm as ssm
from constructs import Construct

from stacks.config import Config


class DatabaseInstanceConstruct(Construct):
    """Values DatabaseInstanceStack publishes, for other stacks to read."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: Config,
    ) -> None:
        super().__init__(scope=scope, id=construct_id)

        self.endpoint = ssm.StringParameter.value_for_string_parameter(
            scope=self,
            parameter_name=f"{config.database_prefix}/instance/endpoint",
        )
        self.resource_id = ssm.StringParameter.value_for_string_parameter(
            scope=self,
            parameter_name=f"{config.database_prefix}/instance/resource-id",
        )
        self.vpc_id = ssm.StringParameter.value_for_string_parameter(
            scope=self,
            parameter_name=f"{config.database_prefix}/vpc/id",
        )
        self.subnet_ids = ssm.StringParameter.value_for_string_parameter(
            scope=self,
            parameter_name=f"{config.database_prefix}/vpc/isolated-subnet-ids",
        )
        self.security_group_id = (
            ssm.StringParameter.value_for_string_parameter(
                scope=self,
                parameter_name=f"{config.database_prefix}/security-group/id",
            )
        )

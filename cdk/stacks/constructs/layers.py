from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from stacks.config import Config


class LayersConstruct(Construct):
    """Shared Lambda layers imported from the ARNs kept in SSM."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: Config,
    ) -> None:
        super().__init__(scope=scope, id=construct_id)

        self.common = lambda_.LayerVersion.from_layer_version_arn(
            scope=self,
            id="Common",
            layer_version_arn=ssm.StringParameter.value_for_string_parameter(
                scope=self,
                parameter_name=f"{config.layers_prefix}/common/arn",
            ),
        )

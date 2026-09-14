import aws_cdk as cdk
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from stacks.config import Config


class CommonLayerStack(cdk.Stack):
    """Builds the shared Lambda layer and publishes its ARN to SSM."""

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

        common = lambda_.LayerVersion(
            scope=self,
            id="CandidateSearchService-common-layer",
            layer_version_name=f"{config.resource_prefix}-common-layer",
            code=lambda_.Code.from_asset(path="../layers/common/build"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_14],
            compatible_architectures=[lambda_.Architecture.X86_64],
            description="SQLAlchemy, psycopg and Alembic",
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        ssm.StringParameter(
            scope=self,
            id="CandidateSearchService-common-layer-arn",
            parameter_name=f"{config.layers_prefix}/common/arn",
            string_value=common.layer_version_arn,
        )

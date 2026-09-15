import aws_cdk as cdk
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from stacks.config import Config


class ModelsLayerStack(cdk.Stack):
    """Ships the ORM models as a layer and publishes its ARN to SSM."""

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

        models = lambda_.LayerVersion(
            scope=self,
            id="CandidateSearchService-models-layer",
            layer_version_name=f"{config.resource_prefix}-models-layer",
            code=lambda_.Code.from_asset(
                path="../layers/models",
                exclude=[
                    "__pycache__",
                    "*.pyc",
                    "*.egg-info",
                    ".ruff_cache",
                    ".mypy_cache",
                    "pyproject.toml",
                ],
            ),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_14],
            compatible_architectures=[lambda_.Architecture.X86_64],
            description="SQLAlchemy models for the candidate tables",
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        ssm.StringParameter(
            scope=self,
            id="CandidateSearchService-models-layer-arn",
            parameter_name=f"{config.layers_prefix}/models/arn",
            string_value=models.layer_version_arn,
        )

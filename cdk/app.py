import aws_cdk as cdk

from stacks.config import Config
from stacks.database.stack import DatabaseStack

app = cdk.App()
config = Config()

DatabaseStack(
    scope=app,
    construct_id=f"{config.resource_prefix}-database",
    config=config,
    description="VPC and RDS Postgres for the candidate search service",
)

app.synth()

import aws_cdk as cdk

from stacks.config import Config
from stacks.database.services.migrations import DatabaseMigrationsStack
from stacks.database.stack import DatabaseStack
from stacks.layers.common import CommonLayerStack

app = cdk.App()
config = Config()

common_layer = CommonLayerStack(
    scope=app,
    construct_id=f"{config.resource_prefix}-common-layer",
    config=config,
    description="Shared Lambda layer for the candidate search service",
)

database = DatabaseStack(
    scope=app,
    construct_id=f"{config.resource_prefix}-database",
    config=config,
    description="VPC and RDS Postgres for the candidate search service",
)

migrations = DatabaseMigrationsStack(
    scope=app,
    construct_id=f"{config.resource_prefix}-database-migrations",
    config=config,
    description="Alembic runner for the candidate search database",
)

migrations.add_stack_dependency(target=common_layer)
migrations.add_stack_dependency(target=database)

app.synth()

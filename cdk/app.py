import aws_cdk as cdk

from stacks.config import Config
from stacks.database.instance import DatabaseInstanceStack
from stacks.database.services.ingest import DatabaseIngestStack
from stacks.database.services.migrations import DatabaseMigrationsStack
from stacks.layers.common import CommonLayerStack
from stacks.layers.models import ModelsLayerStack
from stacks.s3.bucket import S3BucketStack

app = cdk.App()
config = Config()

s3_bucket = S3BucketStack(
    scope=app,
    construct_id=f"{config.resource_prefix}-s3-bucket",
    config=config,
    description="Object storage for the candidate search service",
)

common_layer = CommonLayerStack(
    scope=app,
    construct_id=f"{config.resource_prefix}-common-layer",
    config=config,
    description="Shared Lambda layer for the candidate search service",
)

models_layer = ModelsLayerStack(
    scope=app,
    construct_id=f"{config.resource_prefix}-models-layer",
    config=config,
    description="ORM models layer for the candidate search service",
)

database_instance = DatabaseInstanceStack(
    scope=app,
    construct_id=f"{config.resource_prefix}-database-instance",
    config=config,
    description="VPC and RDS Postgres for the candidate search service",
)

migrations_lambda = DatabaseMigrationsStack(
    scope=app,
    construct_id=f"{config.resource_prefix}-database-migrations-lambda",
    config=config,
    description="Alembic runner for the candidate search database",
)

migrations_lambda.add_stack_dependency(target=common_layer)
migrations_lambda.add_stack_dependency(target=models_layer)
migrations_lambda.add_stack_dependency(target=database_instance)

ingest_lambda = DatabaseIngestStack(
    scope=app,
    construct_id=f"{config.resource_prefix}-database-ingest-lambda",
    config=config,
    description="Resume JSON loader for the candidate search database",
)

ingest_lambda.add_stack_dependency(target=common_layer)
ingest_lambda.add_stack_dependency(target=models_layer)
ingest_lambda.add_stack_dependency(target=database_instance)
ingest_lambda.add_stack_dependency(target=migrations_lambda)

app.synth()

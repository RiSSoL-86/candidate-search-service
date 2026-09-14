import aws_cdk as cdk
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from stacks.config import Config


class S3BucketStack(cdk.Stack):
    """Creates the bucket every service of this project writes to."""

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

        # S3 bucket
        bucket = s3.Bucket(
            scope=self,
            id="CandidateSearchService-s3-bucket",
            bucket_name=config.resource_prefix,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="expire-old-versions",
                    noncurrent_version_expiration=cdk.Duration.days(amount=30),
                    abort_incomplete_multipart_upload_after=cdk.Duration.days(
                        amount=7
                    ),
                )
            ],
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        ssm.StringParameter(
            scope=self,
            id="CandidateSearchService-s3-bucket-name",
            parameter_name=f"{config.s3_prefix}/bucket/name",
            string_value=bucket.bucket_name,
        )

        ssm.StringParameter(
            scope=self,
            id="CandidateSearchService-s3-bucket-arn",
            parameter_name=f"{config.s3_prefix}/bucket/arn",
            string_value=bucket.bucket_arn,
        )

        ssm.StringParameter(
            scope=self,
            id="CandidateSearchService-s3-resumes-prefix",
            parameter_name=f"{config.s3_prefix}/prefixes/resumes",
            string_value="resumes/",
        )

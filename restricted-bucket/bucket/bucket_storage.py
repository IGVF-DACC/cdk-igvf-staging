from aws_cdk import App
from aws_cdk import Duration
from aws_cdk import Stack
from aws_cdk import RemovalPolicy

from aws_cdk.aws_iam import AccountPrincipal
from aws_cdk.aws_iam import ManagedPolicy
from aws_cdk.aws_iam import PolicyStatement

from aws_cdk.aws_s3 import Bucket
from aws_cdk.aws_s3 import CorsRule
from aws_cdk.aws_s3 import HttpMethods
from aws_cdk.aws_s3 import LifecycleRule
from aws_cdk.aws_s3 import StorageClass
from aws_cdk.aws_s3 import Transition

from constructs import Construct

from typing import Any
from typing import List


RESTRICTED_FILES_BUCKET_NAME = 'igvf-restricted-files-staging'


BROWSER_UPLOAD_CORS = CorsRule(
    allowed_methods=[
        HttpMethods.GET,
        HttpMethods.HEAD,
        HttpMethods.POST,
        HttpMethods.PUT,
    ],
    allowed_origins=[
        'https://*-script.googleusercontent.com'
    ],
    allowed_headers=[
        '*',
    ],
    exposed_headers=[
        'Content-Length',
        'Content-Range',
        'Content-Type',
        'ETag',
    ],
    max_age=3000,
)


CORS = CorsRule(
    allowed_methods=[
        HttpMethods.GET,
        HttpMethods.HEAD,
    ],
    allowed_origins=[
        '*'
    ],
    allowed_headers=[
        'Accept',
        'Origin',
        'Range',
        'X-Requested-With',
        'Cache-Control',
    ],
    exposed_headers=[
        'Content-Length',
        'Content-Range',
        'Content-Type',
    ],
    max_age=3000,
)

INTELLIGENT_TIERING_RULE = LifecycleRule(
    id='AllObjectsToIntelligentTieringRule',
    transitions=[
        Transition(
            storage_class=StorageClass.INTELLIGENT_TIERING,
            transition_after=Duration.days(0),
        )
    ]
)

THIRTY_DAYS_EXPIRATION_RULE = LifecycleRule(
    id='ThirtyDaysExpirationRule',
    expiration=Duration.days(30),
)

ABORT_INCOMPLETE_MULTIPART_UPLOAD_RULE = LifecycleRule(
    id='DeleteIncompleteMultipartUploadRule',
    abort_incomplete_multipart_upload_after=Duration.days(7),
)


def generate_read_access_policy_for_bucket(
        *,
        sid: str,
        principals: List[AccountPrincipal],
        resources: List[str]
) -> PolicyStatement:
    return PolicyStatement(
        sid=sid,
        principals=principals,
        resources=resources,
        actions=[
            's3:GetObjectVersion',
            's3:GetObject',
            's3:GetBucketAcl',
            's3:ListBucket',
            's3:GetBucketLocation'
        ]
    )


class RestrictedBucketStorage(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.restricted_files_logs_bucket = Bucket(
            self,
            'RestrictedFilesLogsBucket',
            bucket_name=f'{RESTRICTED_FILES_BUCKET_NAME}-logs',
            removal_policy=RemovalPolicy.RETAIN,
        )

        self.restricted_files_bucket = Bucket(
            self,
            'RestrictedFilesBucket',
            bucket_name=f'{RESTRICTED_FILES_BUCKET_NAME}',
            cors=[
                BROWSER_UPLOAD_CORS,
                CORS
            ],
            removal_policy=RemovalPolicy.RETAIN,
            server_access_logs_bucket=self.restricted_files_logs_bucket,
            versioned=True,
            lifecycle_rules=[
                THIRTY_DAYS_EXPIRATION_RULE,
                ABORT_INCOMPLETE_MULTIPART_UPLOAD_RULE,
                INTELLIGENT_TIERING_RULE,
            ],
        )

from aws_cdk import App
from aws_cdk import Duration
from aws_cdk import Stack
from aws_cdk import RemovalPolicy

from aws_cdk.aws_iam import AccountPrincipal
from aws_cdk.aws_iam import AnyPrincipal
from aws_cdk.aws_iam import ArnPrincipal
from aws_cdk.aws_iam import ManagedPolicy
from aws_cdk.aws_iam import PolicyStatement

from aws_cdk.aws_s3 import BlockPublicAccess
from aws_cdk.aws_s3 import Bucket
from aws_cdk.aws_s3 import BucketMetrics
from aws_cdk.aws_s3 import CorsRule
from aws_cdk.aws_s3 import HttpMethods
from aws_cdk.aws_s3 import LifecycleRule
from aws_cdk.aws_s3 import NoncurrentVersionTransition
from aws_cdk.aws_s3 import StorageClass
from aws_cdk.aws_s3 import Transition

from constructs import Construct

from typing import Any
from typing import List


BLOBS_BUCKET_NAME = 'igvf-blobs-staging'
FILES_BUCKET_NAME = 'igvf-files-staging'
PUBLIC_FILES_BUCKET_NAME = 'igvf-public-staging'
PRIVATE_FILES_BUCKET_NAME = 'igvf-private-staging'

IGVF_TRANSFER_USER_ARN = 'arn:aws:iam::407227577691:user/igvf-files-transfer'

INTELLIGENT_TIERING_RULE = LifecycleRule(
    id='AllObjectsToIntelligentTieringRule',
    transitions=[
        Transition(
            storage_class=StorageClass.INTELLIGENT_TIERING,
            transition_after=Duration.days(0),
        )
    ]
)

ABORT_INCOMPLETE_MULTIPART_UPLOAD_RULE = LifecycleRule(
    id='DeleteIncompleteMultipartUploadRule',
    abort_incomplete_multipart_upload_after=Duration.days(7),
)

NONCURRENT_VERSION_GLACIER_TRANSITION_RULE = LifecycleRule(
    id='OldVersionsToGlacierTransitionRule',
    noncurrent_version_transitions=[
        NoncurrentVersionTransition(
            storage_class=StorageClass.GLACIER,
            transition_after=Duration.days(0),
        )
    ],
    noncurrent_version_expiration=Duration.days(90),
)

TAGGED_OBJECTS_GLACIER_TRANSITION_RULE = LifecycleRule(
    id='TaggedObjectsGlacierTransitionRule',
    tag_filters={'send_to_glacier': 'true'},
    transitions=[
        Transition(
            storage_class=StorageClass.GLACIER,
            transition_after=Duration.days(0),
        )
    ]
)

COPIED_OBJECTS_GLACIER_TRANSITION_RULE = LifecycleRule(
    id='CopiedObjectsGlacierTransitionRule',
    tag_filters={'copied_to': 'open_data_account'},
    transitions=[
        Transition(
            storage_class=StorageClass.GLACIER,
            transition_after=Duration.days(1),
        )
    ]
)

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
        'ETag',
    ],
    max_age=3000,
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


def generate_file_transfer_user_write_policy_for_bucket(
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
            's3:DeleteObject',
            's3:GetBucketAcl',
            's3:GetBucketLocation',
            's3:GetObject',
            's3:GetObjectTagging',
            's3:GetObjectVersion',
            's3:ListBucket',
            's3:PutObject',
            's3:PutObjectTagging',
        ]
    )


class BucketStorage(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.blobs_logs_bucket = Bucket(
            self,
            'BlobsLogsBucket',
            bucket_name=f'{BLOBS_BUCKET_NAME}-logs',
            removal_policy=RemovalPolicy.RETAIN,
        )

        self.blobs_bucket = Bucket(
            self,
            'BlobsBucket',
            bucket_name=f'{BLOBS_BUCKET_NAME}',
            cors=[
                CORS
            ],
            removal_policy=RemovalPolicy.RETAIN,
            server_access_logs_bucket=self.blobs_logs_bucket,
            versioned=True,
            lifecycle_rules=[
                INTELLIGENT_TIERING_RULE,
                ABORT_INCOMPLETE_MULTIPART_UPLOAD_RULE,
                NONCURRENT_VERSION_GLACIER_TRANSITION_RULE,
                TAGGED_OBJECTS_GLACIER_TRANSITION_RULE,
                COPIED_OBJECTS_GLACIER_TRANSITION_RULE,
            ],
        )

        self.files_logs_bucket = Bucket(
            self,
            'FilesLogsBucket',
            bucket_name=f'{FILES_BUCKET_NAME}-logs',
            removal_policy=RemovalPolicy.RETAIN,
        )

        self.files_bucket = Bucket(
            self,
            'FilesBucket',
            bucket_name=f'{FILES_BUCKET_NAME}',
            cors=[
                BROWSER_UPLOAD_CORS,
                CORS
            ],
            removal_policy=RemovalPolicy.RETAIN,
            server_access_logs_bucket=self.files_logs_bucket,
            versioned=True,
            lifecycle_rules=[
                INTELLIGENT_TIERING_RULE,
                ABORT_INCOMPLETE_MULTIPART_UPLOAD_RULE,
                NONCURRENT_VERSION_GLACIER_TRANSITION_RULE,
                TAGGED_OBJECTS_GLACIER_TRANSITION_RULE,
                COPIED_OBJECTS_GLACIER_TRANSITION_RULE,
            ],
        )

        self.private_files_logs_bucket = Bucket(
            self,
            'PrivateFilesLogsBucket',
            bucket_name=f'{PRIVATE_FILES_BUCKET_NAME}-logs',
            removal_policy=RemovalPolicy.RETAIN,
        )

        self.private_files_bucket = Bucket(
            self,
            'PrivateFilesBucket',
            bucket_name=f'{PRIVATE_FILES_BUCKET_NAME}',
            removal_policy=RemovalPolicy.RETAIN,
            cors=[
                CORS
            ],
            metrics=[
                BucketMetrics(
                    id='PrivateFilesBucketMetrics',
                )
            ],
            lifecycle_rules=[
                INTELLIGENT_TIERING_RULE,
                ABORT_INCOMPLETE_MULTIPART_UPLOAD_RULE,
                TAGGED_OBJECTS_GLACIER_TRANSITION_RULE,
                COPIED_OBJECTS_GLACIER_TRANSITION_RULE,
            ],
            server_access_logs_bucket=self.private_files_logs_bucket,
            versioned=False,
        )

        self.public_files_logs_bucket = Bucket(
            self,
            'PublicFilesLogsBucket',
            bucket_name=f'{PUBLIC_FILES_BUCKET_NAME}-logs',
            removal_policy=RemovalPolicy.RETAIN,
        )

        self.public_files_bucket = Bucket(
            self,
            'PublicFilesBucket',
            bucket_name=f'{PUBLIC_FILES_BUCKET_NAME}',
            removal_policy=RemovalPolicy.RETAIN,
            cors=[
                CORS
            ],
            block_public_access=BlockPublicAccess(
                block_public_policy=False,
                restrict_public_buckets=False,
            ),
            metrics=[
                BucketMetrics(
                    id='PublicFilesBucketMetrics',
                )
            ],
            lifecycle_rules=[
                INTELLIGENT_TIERING_RULE,
                ABORT_INCOMPLETE_MULTIPART_UPLOAD_RULE,
            ],
            server_access_logs_bucket=self.public_files_logs_bucket,
            versioned=True,
        )

        self.public_files_bucket_policy_statement = PolicyStatement(
            sid='AllowReadFromPublicFilesBucket',
            principals=[AnyPrincipal()],
            resources=[
                self.public_files_bucket.bucket_arn,
                self.public_files_bucket.arn_for_objects('*'),
            ],
            actions=[
                's3:List*',
                's3:Get*',
            ]
        )

        self.public_files_bucket.add_to_resource_policy(
            self.public_files_bucket_policy_statement,
        )

        self.igvf_transfer_user_principal = ArnPrincipal(
            IGVF_TRANSFER_USER_ARN
        )

        self.public_files_bucket.add_to_resource_policy(
            generate_file_transfer_user_write_policy_for_bucket(
                sid='AllowIgvfTransferUserWritePublicBucket',
                principals=[
                    self.igvf_transfer_user_principal,
                ],
                resources=[
                    self.public_files_bucket.bucket_arn,
                    self.public_files_bucket.arn_for_objects('*'),
                ]
            )
        )

        self.private_files_bucket.add_to_resource_policy(
            generate_file_transfer_user_write_policy_for_bucket(
                sid='AllowIgvfTransferUserWritePrivateBucket',
                principals=[
                    self.igvf_transfer_user_principal,
                ],
                resources=[
                    self.private_files_bucket.bucket_arn,
                    self.private_files_bucket.arn_for_objects('*'),
                ]
            )
        )

        self.igvf_transfer_user_upload_bucket_policy_statement = PolicyStatement(
            sid='AllowIgvfTransferUserReadFromUploadBucket',
            principals=[
                self.igvf_transfer_user_principal
            ],
            resources=[
                self.files_bucket.bucket_arn,
                self.files_bucket.arn_for_objects('*'),
            ],
            actions=[
                's3:GetBucketAcl',
                's3:GetBucketLocation',
                's3:GetObject',
                's3:GetObjectTagging',
                's3:GetObjectVersion',
                's3:ListBucket',
                's3:PutObjectTagging'
            ]
        )

        self.files_bucket.add_to_resource_policy(
            self.igvf_transfer_user_upload_bucket_policy_statement,
        )

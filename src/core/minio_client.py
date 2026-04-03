import boto3
from botocore.exceptions import ClientError
from src.core.config import (
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    AWS_SESSION_TOKEN,
    MINIO_BUCKET
)
import logging

logger = logging.getLogger(__name__)

def get_boto3_client():
    """Returns a connected boto3 client for MinIO or AWS S3."""
    kwargs = {
        'aws_access_key_id': MINIO_ACCESS_KEY,
        'aws_secret_access_key': MINIO_SECRET_KEY,
        'region_name': 'us-east-1'
    }
    
    if AWS_SESSION_TOKEN:
        kwargs['aws_session_token'] = AWS_SESSION_TOKEN
        
    if MINIO_ENDPOINT and 'amazonaws.com' not in MINIO_ENDPOINT:
        kwargs['endpoint_url'] = MINIO_ENDPOINT

    return boto3.client('s3', **kwargs)

def ensure_bucket_exists():
    """Creates the bucket on startup if it doesn't exist."""
    s3 = get_boto3_client()
    try:
        s3.head_bucket(Bucket=MINIO_BUCKET)
        logger.info(f"MinIO bucket '{MINIO_BUCKET}' already exists.")
    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            logger.info(f"MinIO bucket '{MINIO_BUCKET}' not found. Creating...")
            try:
                s3.create_bucket(Bucket=MINIO_BUCKET)
                logger.info(f"MinIO bucket '{MINIO_BUCKET}' created successfully.")
            except ClientError as create_error:
                logger.error(f"Failed to create bucket: {create_error}")
                raise
        else:
            logger.error(f"Error checking bucket: {e}")
            raise

def upload_audio(file_bytes: bytes, storage_key: str, content_type: str) -> str:
    """Uploads file bytes to MinIO and returns the storage_key."""
    s3 = get_boto3_client()
    try:
        s3.put_object(
            Bucket=MINIO_BUCKET,
            Key=storage_key,
            Body=file_bytes,
            ContentType=content_type
        )
        return storage_key
    except ClientError as e:
        logger.error(f"Failed to upload audio to MinIO: {e}")
        raise

def get_presigned_url(storage_key: str, expires: int = 3600) -> str:
    """Returns a temporary download/playback URL."""
    s3 = get_boto3_client()
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': MINIO_BUCKET, 'Key': storage_key},
            ExpiresIn=expires
        )
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise

def download_audio(storage_key: str) -> bytes:
    """Returns raw bytes for the given storage_key."""
    s3 = get_boto3_client()
    try:
        response = s3.get_object(Bucket=MINIO_BUCKET, Key=storage_key)
        return response['Body'].read()
    except ClientError as e:
        logger.error(f"Failed to download audio from MinIO: {e}")
        raise

def delete_audio(storage_key: str):
    """Deletes the audio file from MinIO."""
    s3 = get_boto3_client()
    try:
        s3.delete_object(Bucket=MINIO_BUCKET, Key=storage_key)
    except ClientError as e:
        logger.error(f"Failed to delete audio from MinIO: {e}")
        raise

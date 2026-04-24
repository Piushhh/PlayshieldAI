"""GCS storage service."""

from app.config import get_settings

settings = get_settings()


async def upload_to_gcs(content: bytes, blob_name: str, content_type: str | None = None) -> str:
    """Upload content to Google Cloud Storage. Returns gs:// URI."""
    from google.cloud import storage

    client = storage.Client(project=settings.GCP_PROJECT_ID)
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(content, content_type=content_type)
    return f"gs://{settings.GCS_BUCKET_NAME}/{blob_name}"

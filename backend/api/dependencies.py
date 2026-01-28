# backend/api/dependencies.py
"""FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, UploadFile

from backend.config import Settings, get_settings
from backend.services.llm_client import LLMClient, get_llm_client
from backend.services.storage import StorageService, get_storage_service


def get_config() -> Settings:
    """Get application settings."""
    return get_settings()


def get_llm(settings: Annotated[Settings, Depends(get_config)]) -> LLMClient:
    """Get LLM client."""
    return get_llm_client()


def get_storage(settings: Annotated[Settings, Depends(get_config)]) -> StorageService:
    """Get storage service."""
    return get_storage_service()


async def validate_pdf_upload(
    pdf: UploadFile, settings: Annotated[Settings, Depends(get_config)]
) -> UploadFile:
    """Validate uploaded PDF file."""
    # Check extension
    if not pdf.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Check size
    content = await pdf.read()
    await pdf.seek(0)  # Reset for later reading

    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB",
        )

    return pdf


def validate_job_exists(
    job_id: str, storage: Annotated[StorageService, Depends(get_storage)]
):
    """Validate that job exists."""
    pdf_path = storage.pdf_path(job_id)
    if not storage.exists(pdf_path):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job_id

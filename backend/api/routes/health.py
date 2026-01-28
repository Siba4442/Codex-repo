# backend/api/routes/health.py
"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """Simple health check."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness_check():
    """Readiness check with dependency validation."""
    from backend.config import get_settings
    from backend.services.storage import get_storage_service

    settings = get_settings()
    storage = get_storage_service()

    checks = {
        "config": bool(settings.OPENROUTER_API_KEY),
        "storage": storage.uploads_dir.exists() and storage.outputs_dir.exists(),
    }

    if all(checks.values()):
        return {"status": "ready", "checks": checks}
    else:
        return {"status": "not ready", "checks": checks}

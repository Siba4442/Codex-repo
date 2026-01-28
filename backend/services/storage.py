# backend/services/storage.py
# Handles file uploads and JSON storage

import json
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import UploadFile


class StorageService:
    # Saves PDFs and JSON files

    def __init__(self, uploads_dir: Path, outputs_dir: Path):
        self.uploads_dir = uploads_dir
        self.outputs_dir = outputs_dir

        # Ensure directories exist
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def new_job_id(self) -> str:
        # Create a random job ID
        return uuid.uuid4().hex

    def job_dir(self, job_id: str) -> Path:
        # Get folder for this job
        p = self.outputs_dir / job_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def pdf_path(self, job_id: str) -> Path:
        # Where the PDF is saved
        return self.uploads_dir / f"{job_id}.pdf"

    async def save_pdf(self, job_id: str, pdf: UploadFile) -> Path:
        # Save uploaded PDF file
        dest = self.pdf_path(job_id)
        content = await pdf.read()
        dest.write_bytes(content)
        return dest

    def save_json(self, path: Path, data: Any) -> None:
        # Save data as JSON file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON data from file."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def exists(self, path: Path) -> bool:
        """Check if file exists."""
        return path.exists()

    # Phase-specific paths
    def phase1_raw_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "phase1_categories_raw.json"

    def phase1_reviewed_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "phase1_categories_reviewed.json"

    def phase2_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "phase2_items.json"

    def phase3_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "phase3_bases.json"

    def phase4_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "phase4_final.json"


# Singleton
_storage: StorageService = None


def get_storage_service() -> StorageService:
    """Get cached storage service instance."""
    global _storage
    if _storage is None:
        from backend.config import get_settings

        settings = get_settings()
        _storage = StorageService(
            uploads_dir=settings.UPLOADS_DIR, outputs_dir=settings.OUTPUTS_DIR
        )
    return _storage

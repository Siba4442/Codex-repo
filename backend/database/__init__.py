# backend/database/__init__.py
from backend.database.db import init_db, get_db, engine
from backend.database.models import Restaurant, PhaseData, ExtractionHistory, CategorySizes

# Legacy aliases for backwards compatibility
Job = Restaurant

__all__ = [
    "init_db",
    "get_db",
    "engine",
    "Restaurant",
    "PhaseData",
    "ExtractionHistory",
    "CategorySizes",
    "Job",  # Alias
]

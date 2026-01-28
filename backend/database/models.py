# backend/database/models.py
# Database tables for menu extraction

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Index, Text, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Restaurant(Base):
    # Stores the current state of each menu extraction job

    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    phase = Column(Integer, default=0, nullable=False)
    json = Column(JSON, nullable=True)  # All the extracted menu data
    status = Column(String(50), default="created", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)  # Updates when data changes

    # Links to other tables
    phase_history = relationship(
        "PhaseData", back_populates="job", cascade="all, delete-orphan"
    )
    extraction_logs = relationship(
        "ExtractionHistory", back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_job_status", "job_id", "status"),)


class PhaseData(Base):
    # Keeps the latest result for each phase (1 row per phase per job)

    __tablename__ = "phase_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(32), ForeignKey('restaurants.job_id'), nullable=False, index=True)
    phase = Column(Integer, nullable=False)
    json = Column(JSON, nullable=True)
    status = Column(String(50), default="success", nullable=False)
    datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Links back to the main job
    job = relationship("Restaurant", back_populates="phase_history")

    __table_args__ = (
        UniqueConstraint("job_id", "phase", name="uq_job_phase"),  # Only one row per job per phase
        Index("idx_phase_data_job", "job_id", "phase"),
    )


class ExtractionHistory(Base):
    # Logs every action (extractions, edits, etc.) - keeps full history

    __tablename__ = "extraction_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(32), ForeignKey('restaurants.job_id'), nullable=False, index=True)
    phase = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)  # What happened: extract, manual_edit, etc.
    status = Column(String(20), default="success", nullable=False)
    error_message = Column(Text, nullable=True)
    datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Links back to the main job
    job = relationship("Restaurant", back_populates="extraction_logs")

    __table_args__ = (Index("idx_history_job", "job_id", "phase"),)


class CategorySizes(Base):
    # Stores available sizes per category for a job

    __tablename__ = "category_sizes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(32), ForeignKey('restaurants.job_id'), nullable=False, index=True)
    category_name = Column(String(255), nullable=False)
    sizes_json = Column(JSON, nullable=True)  # Array of {name_raw, size, price}
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Links back to the main job
    job = relationship("Restaurant")

    __table_args__ = (
        UniqueConstraint("job_id", "category_name", name="uq_job_category_sizes"),
        Index("idx_category_sizes_job", "job_id", "category_name"),
    )


# Old names that still work (for backwards compatibility)
Job = Restaurant
JobStatus = None

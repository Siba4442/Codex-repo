# backend/api/routes/jobs.py
# Endpoints for managing extraction jobs

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from backend.database import get_db, Restaurant, PhaseData

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


# Request and response models


class JobListResponse(BaseModel):
    id: int
    job_id: str
    status: str
    current_phase: int
    restaurant_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobDetailResponse(BaseModel):
    id: int
    job_id: str
    status: str
    current_phase: int
    pdf_filename: Optional[str]
    restaurant_name: Optional[str]
    category_count: int
    item_count: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


class UpdateJobStatusRequest(BaseModel):
    status: str
    current_phase: Optional[int] = None


class CategorySummary(BaseModel):
    id: int
    name_raw: str
    description_raw: Optional[str]
    subcategory_count: int
    item_count: int


class SubcategorySummary(BaseModel):
    id: int
    name_raw: str


class CategoryDetailResponse(BaseModel):
    id: int
    name_raw: str
    description_raw: Optional[str]
    subcategories: List[SubcategorySummary]
    item_count: int


# API endpoints


@router.get("/", response_model=List[JobListResponse])
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    # Get all jobs with pagination
    query = db.query(Restaurant)

    if status:
        query = query.filter(Restaurant.status == status)

    restaurants = query.order_by(Restaurant.created_at.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": r.id,
            "job_id": r.job_id,
            "status": r.status,
            "current_phase": r.phase,
            "restaurant_name": r.name,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r in restaurants
    ]


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    # Get details for a specific job
    restaurant = db.query(Restaurant).filter(Restaurant.job_id == job_id).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )

    # Count categories and items from JSON
    category_count = 0
    item_count = 0
    
    if restaurant.json:
        pages = restaurant.json.get("pages", [])
        for page in pages:
            categories = page.get("categories", [])
            category_count += len(categories)
            for cat in categories:
                # Count items in category_items
                for cat_items in cat.get("category_items", []):
                    item_count += len(cat_items.get("items", []))
                # Count items in subcategory_items
                for subcat in cat.get("subcategory_items", []):
                    item_count += len(subcat.get("items", []))

    return JobDetailResponse(
        id=restaurant.id,
        job_id=restaurant.job_id,
        status=restaurant.status,
        current_phase=restaurant.phase,
        pdf_filename=None,
        restaurant_name=restaurant.name,
        category_count=category_count,
        item_count=item_count,
        created_at=restaurant.created_at,
        updated_at=restaurant.updated_at,
        completed_at=restaurant.updated_at if restaurant.phase == 4 else None,
    )


@router.put("/{job_id}/status")
def update_job_status(
    job_id: str, request: UpdateJobStatusRequest, db: Session = Depends(get_db)
):
    # Update job's status and phase
    restaurant = db.query(Restaurant).filter(Restaurant.job_id == job_id).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )

    restaurant.status = request.status if isinstance(request.status, str) else str(request.status)
    if request.current_phase is not None:
        restaurant.phase = request.current_phase

    db.commit()
    db.refresh(restaurant)

    return {
        "success": True,
        "job_id": job_id,
        "status": restaurant.status,
        "current_phase": restaurant.phase,
        "message": "Job status updated",
    }


@router.delete("/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    # Delete a job and all its data
    restaurant = db.query(Restaurant).filter(Restaurant.job_id == job_id).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )

    db.delete(restaurant)
    db.commit()

    return {
        "success": True,
        "job_id": job_id,
        "message": "Job deleted successfully",
    }


# To get categories and items, use the phase endpoints instead (GET /api/phase1/{job_id}, etc.)

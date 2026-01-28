# backend/api/routes/phase2.py
# Endpoints for extracting menu items

from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.dependencies import get_storage
from backend.api.schemas import (
    GetDataResponse,
    Phase2Response,
    UpdateDataRequest,
    UpdateDataResponse,
)
from backend.core.extraction.phase2 import run_phase2
from backend.services.storage import StorageService
from backend.database import get_db, Restaurant, PhaseData, ExtractionHistory, CategorySizes

router = APIRouter(prefix="/api/phase2", tags=["phase2"])


@router.post("/extract", response_model=Phase2Response)
async def extract_items(
    job_id: str,
    storage: Annotated[StorageService, Depends(get_storage)] = None,
    db: Session = Depends(get_db),
):
    # Extract items from the categories
    try:
        # Load inputs
        reviewed_data = storage.load_json(storage.phase1_reviewed_path(job_id))
        pdf_path = storage.pdf_path(job_id)

        if not storage.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF not found")

        # Run extraction
        result = await run_phase2(
            reviewed_data["restaurant_name"], reviewed_data, str(pdf_path)
        )

        # Save output
        storage.save_json(storage.phase2_path(job_id), result)

        # Update database - find existing job
        restaurant = db.query(Restaurant).filter(
            Restaurant.job_id == job_id
        ).first()
        
        if restaurant:
            restaurant.phase = 2
            restaurant.json = result
            restaurant.status = "phase2_complete"
        else:
            raise HTTPException(status_code=404, detail="Job not found")

        # UPSERT PhaseData - replace if exists
        phase_data = db.query(PhaseData).filter(
            PhaseData.job_id == job_id,
            PhaseData.phase == 2
        ).first()
        
        if phase_data:
            phase_data.json = result
            phase_data.status = "success"
            phase_data.datetime = datetime.utcnow()
        else:
            phase_data = PhaseData(
                job_id=job_id,
                phase=2,
                json=result,
                status="success",
            )
            db.add(phase_data)

        # Log extraction
        history = ExtractionHistory(
            job_id=job_id,
            phase=2,
            action="extract",
            status="success",
        )
        db.add(history)

        db.commit()

        return Phase2Response(job_id=job_id, data=result)

    except FileNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Phase 2 failed: {str(e)}")


@router.get("/{job_id}", response_model=GetDataResponse)
async def get_items(
    job_id: str, storage: Annotated[StorageService, Depends(get_storage)] = None
):
    # Get the extracted items
    try:
        data = storage.load_json(storage.phase2_path(job_id))
        return GetDataResponse(job_id=job_id, data=data)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Phase 2 data not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{job_id}", response_model=UpdateDataResponse)
async def update_items(
    job_id: str,
    request: UpdateDataRequest,
    storage: Annotated[StorageService, Depends(get_storage)] = None,
    db: Session = Depends(get_db),
):
    # Save user's edited items
    try:
        from backend.models.domain import CategoryWithItems

        # Validate structure
        for page in request.data["pages"]:
            if "categories" not in page:
                raise HTTPException(status_code=400, detail="Invalid payload structure")
            for cat in page["categories"]:
                CategoryWithItems.model_validate(cat)

        # Save data to file
        storage.save_json(storage.phase2_path(job_id), request.data)

        # Update database
        restaurant = db.query(Restaurant).filter(
            Restaurant.job_id == job_id
        ).first()
        
        if restaurant:
            restaurant.json = request.data
            restaurant.updated_at = datetime.utcnow()
            
            # UPSERT PhaseData
            phase_data = db.query(PhaseData).filter(
                PhaseData.job_id == job_id,
                PhaseData.phase == 2
            ).first()
            
            if phase_data:
                phase_data.json = request.data
                phase_data.datetime = datetime.utcnow()
            
            # Log manual edit
            history = ExtractionHistory(
                job_id=job_id,
                phase=2,
                action="manual_edit",
                status="success",
            )
            db.add(history)
            db.commit()

        return UpdateDataResponse(job_id=job_id)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

# Category Sizes Management Endpoints


@router.get("/{job_id}/categories/{category_name}/sizes")
async def get_category_sizes(
    job_id: str,
    category_name: str,
    db: Session = Depends(get_db),
):
    """Get all available sizes for a category in a job"""
    try:
        # Check if job exists
        restaurant = db.query(Restaurant).filter(
            Restaurant.job_id == job_id
        ).first()
        
        if not restaurant:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get category sizes
        category_sizes = db.query(CategorySizes).filter(
            CategorySizes.job_id == job_id,
            CategorySizes.category_name == category_name,
        ).first()
        
        sizes = category_sizes.sizes_json if category_sizes else []
        return {"job_id": job_id, "category": category_name, "sizes": sizes}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sizes: {str(e)}")


@router.put("/{job_id}/categories/{category_name}/sizes")
async def update_category_sizes(
    job_id: str,
    category_name: str,
    request: dict,
    db: Session = Depends(get_db),
):
    """Update all sizes for a category"""
    try:
        # Check if job exists
        restaurant = db.query(Restaurant).filter(
            Restaurant.job_id == job_id
        ).first()
        
        if not restaurant:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get or create category sizes
        category_sizes = db.query(CategorySizes).filter(
            CategorySizes.job_id == job_id,
            CategorySizes.category_name == category_name,
        ).first()
        
        if category_sizes:
            category_sizes.sizes_json = request.get("sizes", [])
        else:
            category_sizes = CategorySizes(
                job_id=job_id,
                category_name=category_name,
                sizes_json=request.get("sizes", []),
            )
            db.add(category_sizes)
        
        # Log the edit
        history = ExtractionHistory(
            job_id=job_id,
            phase=2,
            action="update_sizes",
            status="success",
        )
        db.add(history)
        db.commit()
        
        return {"job_id": job_id, "category": category_name, "status": "updated"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update sizes: {str(e)}")
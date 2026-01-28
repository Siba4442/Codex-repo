# backend/api/routes/phase1.py
# Endpoints for extracting categories from menu PDFs

from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.api.dependencies import get_storage, validate_pdf_upload
from backend.api.schemas import (
    GetDataResponse,
    Phase1Response,
    UpdateDataRequest,
    UpdateDataResponse,
)
from backend.core.extraction.phase1 import run_phase1
from backend.services.storage import StorageService
from backend.database import get_db, Restaurant, PhaseData, ExtractionHistory

router = APIRouter(prefix="/api/phase1", tags=["phase1"])


@router.post("/extract", response_model=Phase1Response)
async def extract_categories(
    restaurant_name: str = Form(...),
    pdf: UploadFile = File(...),
    storage: Annotated[StorageService, Depends(get_storage)] = None,
    validated_pdf: Annotated[UploadFile, Depends(validate_pdf_upload)] = None,
    db: Session = Depends(get_db),
):
    # Upload PDF and extract categories
    try:
        # Create job
        job_id = storage.new_job_id()

        # Set context for dynamic headers
        from backend.services.llm_client import set_restaurant_context
        set_restaurant_context(restaurant_name)

        # Save PDF
        pdf_path = await storage.save_pdf(job_id, pdf)

        # Run extraction
        result = await run_phase1(restaurant_name, str(pdf_path))

        # Save raw output
        storage.save_json(storage.phase1_raw_path(job_id), result)

        # Also save as reviewed (user can edit later)
        storage.save_json(storage.phase1_reviewed_path(job_id), result)

        # Sync to database - create or update Restaurant
        restaurant = db.query(Restaurant).filter(
            Restaurant.job_id == job_id
        ).first()
        
        if restaurant:
            # Job exists, update it
            restaurant.name = restaurant_name
            restaurant.phase = 1
            restaurant.json = result
            restaurant.status = "phase1_complete"
        else:
            # New job, create it
            restaurant = Restaurant(
                job_id=job_id,
                name=restaurant_name,
                phase=1,
                json=result,
                status="phase1_complete",
            )
            db.add(restaurant)

        # UPSERT PhaseData - replace if exists, insert if not
        phase_data = db.query(PhaseData).filter(
            PhaseData.job_id == job_id,
            PhaseData.phase == 1
        ).first()
        
        if phase_data:
            # Update existing snapshot
            phase_data.json = result
            phase_data.status = "success"
            phase_data.datetime = datetime.utcnow()
        else:
            # Create new snapshot
            phase_data = PhaseData(
                job_id=job_id,
                phase=1,
                json=result,
                status="success",
            )
            db.add(phase_data)

        # Always log extraction attempt
        history = ExtractionHistory(
            job_id=job_id,
            phase=1,
            action="extract",
            status="success",
        )
        db.add(history)

        db.commit()

        return Phase1Response(job_id=job_id, data=result)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Phase 1 failed: {str(e)}")


@router.get("/{job_id}", response_model=GetDataResponse)
async def get_categories(
    job_id: str, storage: Annotated[StorageService, Depends(get_storage)] = None
):
    # Get the extracted categories for editing
    try:
        # Try reviewed first, fallback to raw
        try:
            data = storage.load_json(storage.phase1_reviewed_path(job_id))
        except FileNotFoundError:
            data = storage.load_json(storage.phase1_raw_path(job_id))

        return GetDataResponse(job_id=job_id, data=data)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Phase 1 data not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{job_id}", response_model=UpdateDataResponse)
async def update_categories(
    job_id: str,
    request: UpdateDataRequest,
    storage: Annotated[StorageService, Depends(get_storage)] = None,
    db: Session = Depends(get_db),
):
    # Save user's edited categories
    try:
        from backend.models.domain import Categories

        # Validate structure
        for page in request.data["pages"]:
            if "data" not in page:
                raise HTTPException(status_code=400, detail="Invalid payload structure")
            Categories.model_validate(page["data"])

        # Save reviewed data to file
        storage.save_json(storage.phase1_reviewed_path(job_id), request.data)

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
                PhaseData.phase == 1
            ).first()
            
            if phase_data:
                phase_data.json = request.data
                phase_data.datetime = datetime.utcnow()
            
            # Log manual edit
            history = ExtractionHistory(
                job_id=job_id,
                phase=1,
                action="manual_edit",
                status="success",
            )
            db.add(history)
            db.commit()

        return UpdateDataResponse(job_id=job_id)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

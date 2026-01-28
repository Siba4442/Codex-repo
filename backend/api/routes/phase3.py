# backend/api/routes/phase3.py
# Endpoints for extracting item variations

from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.dependencies import get_storage
from backend.api.schemas import (
    GetDataResponse,
    Phase3Response,
    UpdateDataRequest,
    UpdateDataResponse,
)
from backend.core.extraction.phase3 import run_phase3
from backend.services.storage import StorageService
from backend.database import get_db, Restaurant, PhaseData, ExtractionHistory

router = APIRouter(prefix="/api/phase3", tags=["phase3"])


@router.post("/extract", response_model=Phase3Response)
async def extract_bases(
    job_id: str,
    storage: Annotated[StorageService, Depends(get_storage)] = None,
    db: Session = Depends(get_db),
):
    # Extract item variations (sizes, etc.)
    try:
        items_data = storage.load_json(storage.phase2_path(job_id))
        pdf_path = storage.pdf_path(job_id)

        if not storage.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF not found")

        result = await run_phase3(
            items_data["restaurant_name"], items_data, str(pdf_path)
        )

        storage.save_json(storage.phase3_path(job_id), result)

        # Update database
        restaurant = db.query(Restaurant).filter(
            Restaurant.job_id == job_id
        ).first()
        
        if restaurant:
            restaurant.phase = 3
            restaurant.json = result
            restaurant.status = "phase3_complete"
        else:
            raise HTTPException(status_code=404, detail="Job not found")

        # UPSERT PhaseData
        phase_data = db.query(PhaseData).filter(
            PhaseData.job_id == job_id,
            PhaseData.phase == 3
        ).first()
        
        if phase_data:
            phase_data.json = result
            phase_data.status = "success"
            phase_data.datetime = datetime.utcnow()
        else:
            phase_data = PhaseData(
                job_id=job_id,
                phase=3,
                json=result,
                status="success",
            )
            db.add(phase_data)

        # Log extraction
        history = ExtractionHistory(
            job_id=job_id,
            phase=3,
            action="extract",
            status="success",
        )
        db.add(history)

        db.commit()

        return Phase3Response(job_id=job_id, data=result)

    except FileNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Phase 3 failed: {str(e)}")


@router.get("/{job_id}", response_model=GetDataResponse)
async def get_bases(
    job_id: str, storage: Annotated[StorageService, Depends(get_storage)] = None
):
    """Get Phase 3 bases for editing."""
    try:
        data = storage.load_json(storage.phase3_path(job_id))
        return GetDataResponse(job_id=job_id, data=data)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Phase 3 data not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{job_id}", response_model=UpdateDataResponse)
async def update_bases(
    job_id: str,
    request: UpdateDataRequest,
    storage: Annotated[StorageService, Depends(get_storage)] = None,
    db: Session = Depends(get_db),
):
    """Save edited Phase 3 bases."""
    try:
        from backend.models.domain import CategoryWithItems

        for page in request.data["pages"]:
            if "categories" not in page:
                raise HTTPException(status_code=400, detail="Invalid payload structure")
            for cat in page["categories"]:
                CategoryWithItems.model_validate(cat)

        # Save to file
        storage.save_json(storage.phase3_path(job_id), request.data)

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
                PhaseData.phase == 3
            ).first()
            
            if phase_data:
                phase_data.json = request.data
                phase_data.datetime = datetime.utcnow()
            
            # Log manual edit
            history = ExtractionHistory(
                job_id=job_id,
                phase=3,
                action="manual_edit",
                status="success",
            )
            db.add(history)
            db.commit()

        return UpdateDataResponse(job_id=job_id)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

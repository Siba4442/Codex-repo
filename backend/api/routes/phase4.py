# backend/api/routes/phase4.py
# Endpoints for extracting add-ons and final menu data

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.dependencies import get_storage
from backend.api.schemas import (
    GetDataResponse,
    Phase4Response,
    UpdateDataRequest,
    UpdateDataResponse,
)
from backend.core.extraction.phase4 import run_phase4
from backend.services.storage import StorageService
from backend.database import get_db, Restaurant, PhaseData, ExtractionHistory
from datetime import datetime

router = APIRouter(prefix="/api/phase4", tags=["phase4"])


@router.post("/extract", response_model=Phase4Response)
async def extract_addons(
    job_id: str,
    storage: Annotated[StorageService, Depends(get_storage)] = None,
    db: Session = Depends(get_db),
):
    # Extract add-ons and create final complete menu
    try:
        items_data = storage.load_json(storage.phase2_path(job_id))
        bases_data = storage.load_json(storage.phase3_path(job_id))
        pdf_path = storage.pdf_path(job_id)

        if not storage.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF not found")

        result = await run_phase4(
            items_data["restaurant_name"], items_data, bases_data, str(pdf_path)
        )

        storage.save_json(storage.phase4_path(job_id), result)

        # Update database
        restaurant = db.query(Restaurant).filter(
            Restaurant.job_id == job_id
        ).first()
        
        if restaurant:
            restaurant.phase = 4
            restaurant.json = result
            restaurant.status = "phase4_complete"
        else:
            raise HTTPException(status_code=404, detail="Job not found")

        # UPSERT PhaseData
        phase_data = db.query(PhaseData).filter(
            PhaseData.job_id == job_id,
            PhaseData.phase == 4
        ).first()
        
        if phase_data:
            phase_data.json = result
            phase_data.status = "success"
            phase_data.datetime = datetime.utcnow()
        else:
            phase_data = PhaseData(
                job_id=job_id,
                phase=4,
                json=result,
                status="success",
            )
            db.add(phase_data)

        # Log extraction
        history = ExtractionHistory(
            job_id=job_id,
            phase=4,
            action="extract",
            status="success",
        )
        db.add(history)

        db.commit()

        return Phase4Response(job_id=job_id, data=result)

    except FileNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Phase 4 failed: {str(e)}")


@router.get("/{job_id}", response_model=GetDataResponse)
async def get_final_result(
    job_id: str, storage: Annotated[StorageService, Depends(get_storage)] = None
):
    """Get Phase 4 final result."""
    try:
        data = storage.load_json(storage.phase4_path(job_id))
        return GetDataResponse(job_id=job_id, data=data)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Phase 4 data not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{job_id}", response_model=UpdateDataResponse)
async def update_final_result(
    job_id: str,
    request: UpdateDataRequest,
    storage: Annotated[StorageService, Depends(get_storage)] = None,
    db: Session = Depends(get_db),
):
    """Update Phase 4 final result."""
    try:
        from backend.models.domain import CategoryItemAddons

        # Validate structure
        if "categories" in request.data:
            for category in request.data["categories"]:
                CategoryItemAddons.model_validate(category)

        # Save updated data to file
        storage.save_json(storage.phase4_path(job_id), request.data)

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
                PhaseData.phase == 4
            ).first()
            
            if phase_data:
                phase_data.json = request.data
                phase_data.datetime = datetime.utcnow()
            
            # Log manual edit
            history = ExtractionHistory(
                job_id=job_id,
                phase=4,
                action="manual_edit",
                status="success",
            )
            db.add(history)
            db.commit()

        return UpdateDataResponse(job_id=job_id)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

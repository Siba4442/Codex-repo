# backend/api/schemas.py
"""API request/response schemas."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class JobCreatedResponse(BaseModel):
    success: bool = True
    job_id: str
    message: str = "Job created successfully"


class Phase1Response(BaseModel):
    success: bool = True
    job_id: str
    data: Dict[str, Any]
    message: str = "Phase 1 extraction complete"


class Phase2Response(BaseModel):
    success: bool = True
    job_id: str
    data: Dict[str, Any]
    message: str = "Phase 2 extraction complete"


class Phase3Response(BaseModel):
    success: bool = True
    job_id: str
    data: Dict[str, Any]
    message: str = "Phase 3 extraction complete"


class Phase4Response(BaseModel):
    success: bool = True
    job_id: str
    data: Dict[str, Any]
    message: str = "Phase 4 extraction complete"


class GetDataResponse(BaseModel):
    success: bool = True
    job_id: str
    data: Dict[str, Any]


class UpdateDataRequest(BaseModel):
    job_id: str
    data: Dict[str, Any]


class UpdateDataResponse(BaseModel):
    success: bool = True
    job_id: str
    message: str = "Data updated successfully"


class ReextractRequest(BaseModel):
    job_id: str
    page_number: int
    category_name: str


class ReextractResponse(BaseModel):
    success: bool = True
    job_id: str
    page_number: int
    category_name: str
    data: Dict[str, Any]
    message: str = "Re-extraction complete"


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None

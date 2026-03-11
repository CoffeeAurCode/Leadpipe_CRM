from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID


class SmsWorkflowRequest(BaseModel):
    tenant_ids: List[UUID] = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class SmsResult(BaseModel):
    tenant_id: UUID
    success: bool
    sid: Optional[str] = None


class SmsWorkflowResponse(BaseModel):
    results: List[SmsResult]

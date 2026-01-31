from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import CallLog
from typing import List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/call_logs", tags=["CallLogs"])


class CallLogResponse(BaseModel):
    id: int
    call_id: str | None
    phone_number: str | None
    transcript: str | None
    raw_event_type: str | None
    complaint_status: str | None
    created_at: datetime
    complaint_id: int | None
    
    class Config:
        from_attributes = True


@router.get("", response_model=List[CallLogResponse])
async def get_all_call_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CallLog).order_by(CallLog.created_at.desc())
    )
    call_logs = result.scalars().all()
    return call_logs

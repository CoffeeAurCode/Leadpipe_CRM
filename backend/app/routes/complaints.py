from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import Complaint
from app.schemas.complaint import ComplaintCreate, ComplaintUpdate, ComplaintResponse

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.post("", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def create_complaint(
    complaint_data: ComplaintCreate,
    db: AsyncSession = Depends(get_db)
):
    complaint = Complaint(**complaint_data.model_dump())
    db.add(complaint)
    await db.commit()
    await db.refresh(complaint)
    return complaint


@router.get("", response_model=list[ComplaintResponse])
async def get_all_complaints(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Complaint).order_by(Complaint.created_at.desc())
    )
    complaints = result.scalars().all()
    return complaints


@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint_by_id(
    complaint_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Complaint).where(Complaint.id == complaint_id)
    )
    complaint = result.scalars().first()
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with id {complaint_id} not found"
        )
    
    return complaint


@router.patch("/{complaint_id}", response_model=ComplaintResponse)
async def update_complaint(
    complaint_id: int,
    complaint_data: ComplaintUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Complaint).where(Complaint.id == complaint_id)
    )
    complaint = result.scalars().first()
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with id {complaint_id} not found"
        )
    
    update_data = complaint_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(complaint, field, value)
    
    await db.commit()
    await db.refresh(complaint)
    return complaint

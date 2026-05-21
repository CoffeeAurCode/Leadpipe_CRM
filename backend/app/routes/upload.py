from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from supabase import Client
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription
from app.db.session import get_service_db
from typing import Optional
from uuid import uuid4

router = APIRouter(prefix="/upload", tags=["Upload"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ALLOWED_DOC_TYPES = {"application/pdf"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
MAX_DOC_SIZE_BYTES  = 10 * 1024 * 1024
IMAGE_BUCKET = "Property Pics"
DOC_BUCKET = "Tenant_docs"


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    entity_type: Optional[str] = Form("misc"),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
    svc: Client = Depends(get_service_db),
):
    is_doc = entity_type == "tenant_document"
    allowed = ALLOWED_DOC_TYPES if is_doc else ALLOWED_IMAGE_TYPES
    bucket = DOC_BUCKET if is_doc else IMAGE_BUCKET

    if file.content_type not in allowed:
        allowed_label = "pdf" if is_doc else "jpg, jpeg, png, webp"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Allowed: {allowed_label}.",
        )

    max_size = MAX_DOC_SIZE_BYTES if is_doc else MAX_IMAGE_SIZE_BYTES
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large ({len(contents) // 1024} KB). Maximum: {'10 MB' if is_doc else '5 MB'}.",
        )

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    safe_type = entity_type.strip().lower() or "misc"
    storage_path = f"{safe_type}/{uuid4()}.{ext}"

    try:
        svc.storage.from_(bucket).upload(
            storage_path,
            contents,
            {"content-type": file.content_type},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage upload failed: {str(e)}",
        )

    try:
        public_url = svc.storage.from_(bucket).get_public_url(storage_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get public URL: {str(e)}",
        )

    return {"url": public_url, "path": storage_path}

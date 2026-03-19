"""
Image Upload API Route

Provides a single upload endpoint for any entity type (property, building, unit).
Uploads to the existing 'Property Pics' Supabase Storage bucket and returns the public URL.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from supabase import Client, create_client
from app.db.session import get_db
from app.config import settings
from typing import Optional
from uuid import uuid4

router = APIRouter(prefix="/upload", tags=["Upload"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ALLOWED_DOC_TYPES = {"application/pdf"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024   # 5 MB
MAX_DOC_SIZE_BYTES  = 10 * 1024 * 1024  # 10 MB
IMAGE_BUCKET = "Property Pics"
DOC_BUCKET = "Tenant_docs"


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    entity_type: Optional[str] = Form("misc"),  # e.g. property | building | unit | tenant_document
    db: Client = Depends(get_db),
):
    """
    Upload a file to Supabase Storage and return its public URL.

    - For entity_type="tenant_document": uploads to Tenant_docs bucket, allows PDFs + images
    - Otherwise: uploads to Property Pics bucket, images only
    - Validates file size (max 5 MB)
    - Generates a unique filename: {entity_type}/{uuid}.{ext}
    - Returns: { "url": "<public url>" }
    """
    is_doc = entity_type == "tenant_document"
    allowed = ALLOWED_DOC_TYPES if is_doc else ALLOWED_IMAGE_TYPES
    bucket = DOC_BUCKET if is_doc else IMAGE_BUCKET

    # ── Validate MIME type ────────────────────────────────────────────────────
    if file.content_type not in allowed:
        allowed_label = "pdf" if is_doc else "jpg, jpeg, png, webp"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Allowed: {allowed_label}.",
        )

    # ── Read & validate size ──────────────────────────────────────────────────
    max_size = MAX_DOC_SIZE_BYTES if is_doc else MAX_IMAGE_SIZE_BYTES
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large ({len(contents) // 1024} KB). Maximum: {'10 MB' if is_doc else '5 MB'}.",
        )

    # ── Build unique storage path ─────────────────────────────────────────────
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    safe_type = entity_type.strip().lower() or "misc"
    storage_path = f"{safe_type}/{uuid4()}.{ext}"

    # ── Build service-role storage client (bypasses RLS on storage buckets) ──
    svc_key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
    svc_url = settings.SUPABASE_URL.rstrip("/") + "/"
    storage_client = create_client(svc_url, svc_key)

    # ── Upload to Supabase Storage ────────────────────────────────────────────
    try:
        storage_client.storage.from_(bucket).upload(
            storage_path,
            contents,
            {"content-type": file.content_type},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage upload failed: {str(e)}",
        )

    # ── Get public URL ────────────────────────────────────────────────────────
    try:
        public_url = storage_client.storage.from_(bucket).get_public_url(storage_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get public URL: {str(e)}",
        )

    return {"url": public_url, "path": storage_path}

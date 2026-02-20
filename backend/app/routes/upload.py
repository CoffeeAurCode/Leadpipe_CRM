"""
Image Upload API Route

Provides a single upload endpoint for any entity type (property, building, unit).
Uploads to the existing 'Property Pics' Supabase Storage bucket and returns the public URL.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from supabase import Client
from app.db.session import get_db
from typing import Optional
from uuid import uuid4

router = APIRouter(prefix="/upload", tags=["Upload"])

ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
BUCKET_NAME = "Property Pics"


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    entity_type: Optional[str] = Form("misc"),  # e.g. property | building | unit
    db: Client = Depends(get_db),
):
    """
    Upload an image to Supabase Storage and return its public URL.

    - Validates file type (jpg, jpeg, png, webp only)
    - Validates file size (max 5 MB)
    - Generates a unique filename: {entity_type}/{uuid}.{ext}
    - Returns: { "url": "<public url>" }
    """
    # ── Validate MIME type ────────────────────────────────────────────────────
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Allowed: jpg, jpeg, png, webp.",
        )

    # ── Read & validate size ──────────────────────────────────────────────────
    contents = await file.read()
    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large ({len(contents) // 1024} KB). Maximum: 5 MB.",
        )

    # ── Build unique storage path ─────────────────────────────────────────────
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    safe_type = entity_type.strip().lower() or "misc"
    storage_path = f"{safe_type}/{uuid4()}.{ext}"

    # ── Upload to Supabase Storage ────────────────────────────────────────────
    try:
        db.storage.from_(BUCKET_NAME).upload(
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
        public_url = db.storage.from_(BUCKET_NAME).get_public_url(storage_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get public URL: {str(e)}",
        )

    return {"url": public_url, "path": storage_path}

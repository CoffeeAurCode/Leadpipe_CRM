# Learning Guide Session 13: File Uploads, Multipart Forms, Action-Based PATCH APIs, and Production Debugging

**Role:** Senior Staff Engineer Mentorship
**Objective:** Master file upload handling with Supabase Storage, multipart/form-data vs JSON, Pydantic-based action dispatch patterns, and diagnosing 422/500 errors caused by unsafe attribute access.

---

## 1. Overview of What Was Built in This Session

Two major milestones were accomplished:

**Feature 1: Add Property (multipart form + image upload)**
- Backend: `POST /flats` with `Form()` fields + optional `UploadFile` for the property image
- Image upload pipeline to Supabase Storage ("Property Pics" bucket) with public URL retrieval
- Transactional cleanup: if the DB insert fails after image upload, the orphaned image is deleted
- Optional tenant creation and flat-linking in one request

**Feature 2: Flat Editing — Restoring Structural Integrity**
- Identified and fixed the root cause of `422 Unprocessable Entity` and `500 Internal Server Error` on `PATCH /flats/{uuid}`
- Introduced a new `FlatEditRequest` schema with an explicit `action` discriminator field
- Replaced inconsistent `flat.occupied` boolean logic with a single source of truth: `flat.tenant_uuid`
- Added `FlatResponse.model_validate()` for strict schema enforcement on output

---

## 2. Core Concept: `multipart/form-data` vs `application/json`

### The Problem with JSON for File Uploads

Standard JSON is text-only. It cannot represent binary data (images, PDFs) without base64 encoding, which bloats file size by ~33% and is CPU-intensive.

```
❌ BAD APPROACH:
POST /flats
Content-Type: application/json

{
  "flat_number": "A101",
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ..."  // ← bloated base64
}
```

### The Solution: multipart/form-data

`multipart/form-data` is an encoding that lets you send text fields AND binary files in the same request. Each part has its own headers and body, separated by a boundary string.

```
POST /flats
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW

------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="flat_number"

A101
------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="image"; filename="photo.jpg"
Content-Type: image/jpeg

[binary image data]
------WebKitFormBoundary7MA4YWxkTrZu0gW--
```

**Mental Model:** Think of multipart like an email with attachments. The text fields are in the email body; the image is an attachment. The "boundary" string is the divider between each part.

### Decision Table

| Scenario | Use |
|----------|-----|
| Pure data (strings, numbers, booleans, nested objects) | `application/json` |
| One file only, no extra fields | `multipart/form-data` |
| File + additional fields together | `multipart/form-data` |
| Large binary streams | `multipart/form-data` |
| Public APIs that need to be simple to call | `application/json` for data, separate file endpoint |

---

## 3. FastAPI: `Form()`, `File()`, and `UploadFile`

### The Critical Dependency: python-multipart

**Error you will definitely hit:**
```
RuntimeError: Form data requires "python-multipart" to be installed.
Please install it with:
    pip install python-multipart
```

**Root Cause:** FastAPI does not ship with multipart parsing. It delegates this to the `python-multipart` library.

**Fix:**
```bash
pip install python-multipart
```

Then add it to `requirements.txt`:
```
python-multipart==0.0.9
```

**Why this error is confusing:** The server starts fine. You only see this error the moment the first multipart request hits. It looks like a runtime crash, not a missing dependency.

### How FastAPI Declares Form Fields

```python
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional

@router.post("", response_model=FlatResponse, status_code=status.HTTP_201_CREATED)
async def create_flat(
    # Text fields come in via Form()
    flat_number: str = Form(...),                    # Required
    address: Optional[str] = Form(None),             # Optional
    floor_number: Optional[int] = Form(None),        # Integers work too
    bedrooms: Optional[int] = Form(None),

    # File field comes in via File() / UploadFile
    image: Optional[UploadFile] = File(None),        # Optional file

    # Dependency injection still works normally
    db: Client = Depends(get_db)
):
```

**Critical Rule:** When ANY parameter in a route uses `Form()`, ALL body parameters must use `Form()`. You CANNOT mix `Form()` and a Pydantic request body model (`BaseModel`) in the same endpoint. FastAPI will raise an error.

```python
# ❌ WRONG — You cannot mix Form() and a Pydantic body
async def create_flat(
    flat_number: str = Form(...),
    data: FlatCreate,  # ← This would conflict with Form()
    ...
):

# ✅ RIGHT — All fields from form separately
async def create_flat(
    flat_number: str = Form(...),
    address: Optional[str] = Form(None),
    ...
):
```

### UploadFile — What It Is and How to Use It

`UploadFile` is FastAPI's wrapper around an uploaded file. It provides:
- `filename` — the original filename the client sent
- `content_type` — the MIME type (e.g., `image/jpeg`)
- `read()` — async method to read file bytes into memory
- `seek(0)` — async method to reset the read position

```python
if image:
    # Check content type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # Read all bytes into memory
    contents = await image.read()

    # Check file size (10MB limit)
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size: 10MB")

    # Get file extension safely
    file_ext = image.filename.split('.')[-1] if '.' in image.filename else 'jpg'
```

**Why `await image.read()`?** Files are read asynchronously to avoid blocking the event loop during I/O.

---

## 4. Supabase Storage: Uploading Images and Getting Public URLs

### Bucket Setup (One-Time in Supabase Dashboard)

1. Go to your Supabase project → Storage → Create bucket
2. Bucket name: `Property Pics` (exact name matters — matches code)
3. Set **Public** if you want public URLs (required for displaying in frontend)

### Upload to Supabase Storage

```python
from uuid import uuid4

# Always use UUIDs for filenames — never use the original filename!
# Original filenames can have spaces, non-ASCII chars, path traversal attacks
file_ext = image.filename.split('.')[-1] if '.' in image.filename else 'jpg'
uploaded_filename = f"{uuid4()}.{file_ext}"

# Upload
upload_response = db.storage.from_("Property Pics").upload(
    uploaded_filename,         # Path/name in the bucket
    contents,                  # Raw bytes
    {"content-type": image.content_type}  # Content-Type header
)

# Get the public URL after upload
image_url = db.storage.from_("Property Pics").get_public_url(uploaded_filename)
```

**Why UUID filenames?**
- `photo.jpg` → second upload overwrites the first
- `my photo.jpg` → URL encoding issues
- `../../etc/passwd` → path traversal attack
- `550e8400-e29b-41d4-a716-446655440000.jpg` → unique, safe, no conflicts

### The Transactional Cleanup Pattern

**The Problem:** You upload the image, then the DB insert fails. Now you have an orphaned image in storage with no corresponding database record. Over time this wastes storage quota.

**Solution:** Wrap the entire operation in try/except, and delete the uploaded image if anything after the upload fails.

```python
image_url = None
uploaded_filename = None  # Track this so we can clean up

try:
    # Step 1: Upload image
    if image:
        uploaded_filename = f"{uuid4()}.jpg"
        db.storage.from_("Property Pics").upload(uploaded_filename, contents, ...)
        image_url = db.storage.from_("Property Pics").get_public_url(uploaded_filename)

    # Step 2: Check for duplicate flat number
    existing = db.table("flats").select("*").eq("flat_number", flat_number).execute()
    if existing.data:
        # CLEANUP before raising — the image was already uploaded!
        if uploaded_filename:
            db.storage.from_("Property Pics").remove([uploaded_filename])
        raise HTTPException(status_code=400, detail="Flat already exists")

    # Step 3: Insert flat
    flat_response = db.table("flats").insert(flat_payload).execute()
    if not flat_response.data:
        if uploaded_filename:
            db.storage.from_("Property Pics").remove([uploaded_filename])
        raise HTTPException(status_code=500, detail="Failed to create flat")

except HTTPException:
    raise  # Re-raise HTTP exceptions as-is
except Exception as e:
    # Catch-all cleanup on unexpected errors
    if uploaded_filename:
        try:
            db.storage.from_("Property Pics").remove([uploaded_filename])
        except:
            pass  # Best effort cleanup, don't hide the original error
    raise HTTPException(status_code=500, detail=f"Error creating flat: {str(e)}")
```

**The `remove()` takes a list** — even for a single file:
```python
db.storage.from_("Property Pics").remove([uploaded_filename])  # ← note the list
```

---

## 5. Testing Multipart Endpoints with curl

### Basic curl for multipart

```bash
# POST with flat_number field only (no image)
curl -X POST http://localhost:8000/flats \
  -F "flat_number=A101" \
  -F "address=123 Main St" \
  -F "bedrooms=2"

# POST with an image file
curl -X POST http://localhost:8000/flats \
  -F "flat_number=A102" \
  -F "address=123 Main St" \
  -F "image=@/path/to/photo.jpg"
```

**Why `-F` not `-d`?**
- `-d` → sends `application/x-www-form-urlencoded` or raw body (can't attach files)
- `-F` → sends `multipart/form-data` with proper boundaries

**Why `@` before the file path?**
The `@` prefix tells curl to read the actual file contents from disk, not treat the string literally.

### Error Case Testing

```bash
# Test missing required field → should get 422
curl -X POST http://localhost:8000/flats \
  -F "address=123 Main St"
# Expected: {"detail": [{"loc": ["body", "flat_number"], "msg": "Field required", ...}]}

# Test invalid file type → should get 400
curl -X POST http://localhost:8000/flats \
  -F "flat_number=A103" \
  -F "image=@/path/to/document.pdf"
# Expected: {"detail": "Invalid file type. Allowed: image/jpeg, image/jpg, image/png, image/webp"}

# Test duplicate flat → should get 400
curl -X POST http://localhost:8000/flats \
  -F "flat_number=A101"  # Already created above
# Expected: {"detail": "Flat A101 already exists"}
```

---

## 6. React Frontend: Sending FormData

When the backend expects `multipart/form-data`, the frontend must use the browser's `FormData` API.

```javascript
// frontend/src/services/apiService.js

export async function createProperty(formValues) {
    const formData = new FormData();

    // Append text fields
    formData.append('flat_number', formValues.flatNumber);
    if (formValues.address) formData.append('address', formValues.address);
    if (formValues.bedrooms) formData.append('bedrooms', formValues.bedrooms.toString());

    // Append file (if provided)
    if (formValues.image instanceof File) {
        formData.append('image', formValues.image);
        // Note: FormData automatically sets Content-Type to multipart/form-data
        // with the correct boundary — you MUST NOT set it manually!
    }

    const response = await fetch(`${API_BASE_URL}/flats`, {
        method: 'POST',
        body: formData,
        // ⚠️ DO NOT set Content-Type header here!
        // The browser sets it automatically with the boundary string.
        // If you set it manually, the boundary won't be included and the server
        // will fail to parse the request body.
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create property');
    }

    return response.json();
}
```

**The #1 Mistake with FormData:**
```javascript
// ❌ WRONG — This breaks multipart because boundary is missing
headers: {
    'Content-Type': 'multipart/form-data'
}

// ✅ RIGHT — Don't set Content-Type at all for FormData
// The browser handles it automatically:
// Content-Type: multipart/form-data; boundary=----WebKitFormBoundary...
```

### File Input in React

```jsx
function AddPropertyModal({ onSubmit }) {
    const [flatNumber, setFlatNumber] = useState('');
    const [imageFile, setImageFile] = useState(null);
    const [imagePreview, setImagePreview] = useState(null);

    const handleImageChange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        setImageFile(file);

        // Create a local preview URL (doesn't upload yet)
        const url = URL.createObjectURL(file);
        setImagePreview(url);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        await onSubmit({ flatNumber, image: imageFile });
    };

    return (
        <form onSubmit={handleSubmit}>
            <input
                type="text"
                value={flatNumber}
                onChange={(e) => setFlatNumber(e.target.value)}
                placeholder="Flat Number (e.g., A101)"
                required
            />

            {/* File input — accept only images */}
            <input
                type="file"
                accept="image/*"
                onChange={handleImageChange}
            />

            {/* Preview the selected image before upload */}
            {imagePreview && (
                <img src={imagePreview} alt="Preview" className="w-32 h-32 object-cover" />
            )}

            <button type="submit">Add Property</button>
        </form>
    );
}
```

---

## 7. The 422 Unprocessable Entity — Deep Dive

### What Causes 422

HTTP 422 means "the server understood the request format but the data inside it failed validation." In FastAPI, this is always caused by Pydantic validation failing.

**Common triggers:**
1. Missing required field
2. Wrong type (e.g., string where integer expected)
3. Value out of allowed range
4. None sent where the schema requires a value

### Anatomy of a 422 Response

```json
{
    "detail": [
        {
            "type": "missing",
            "loc": ["body", "action"],
            "msg": "Field required",
            "input": {"flat_details": null}
        }
    ]
}
```

Reading the `loc` array:
- `"body"` → the error is in the request body
- `"action"` → specifically the `action` field

### The Bug That Caused 422 in This Session

**Original schema (before fix):**
```python
class FlatEditRequest(BaseModel):
    flat_details: Optional[FlatUpdate] = None
    # No action field — the route was trying to handle multiple operations
    # without a clear discriminator
```

**What the frontend sent:**
```json
{
    "action": "ADD_TENANT",
    "tenant_data": {"name": "John", "phone": "+1234567890"}
}
```

**Why 422?** The original schema didn't have an `action` field, so Pydantic rejected the input with "Extra inputs are not permitted" (or silently ignored it, depending on config).

**The Fix — Explicit Action Field:**
```python
# backend/app/schemas/flat_update.py

from pydantic import BaseModel, Field
from typing import Optional, Literal
from app.schemas.flat import FlatUpdate

class TenantUpdate(BaseModel):
    name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=10)

class FlatEditRequest(BaseModel):
    flat_details: Optional[FlatUpdate] = None  # Optional flat property changes

    # Literal type = only these exact string values are valid
    action: Literal['UPDATE_FLAT_ONLY', 'ADD_TENANT', 'UPDATE_TENANT', 'REMOVE_TENANT']

    tenant_data: Optional[TenantUpdate] = None  # Required for ADD/UPDATE_TENANT
```

**Why `Literal` type?** It acts like an enum directly in Pydantic. If the client sends `action: "DELETE_TENANT"` (wrong), Pydantic immediately returns 422 with a clear message:
```
Input should be 'UPDATE_FLAT_ONLY', 'ADD_TENANT', 'UPDATE_TENANT' or 'REMOVE_TENANT'
```

---

## 8. The 500 Internal Server Error from Unsafe Attribute Access

### The Bug

```python
# ❌ ORIGINAL BUGGY CODE
async def update_flat_details(flat_uuid: str, request: FlatEditRequest, ...):
    # BUG: If request.flat_details is None, this crashes with AttributeError
    flat_update_payload = request.flat_details.model_dump(exclude_unset=True)
    #                     ^^^^^^^^^^^^^^^^^^^
    # AttributeError: 'NoneType' object has no attribute 'model_dump'
```

**Error message you would see:**
```
AttributeError: 'NoneType' object has no attribute 'model_dump'
```

FastAPI catches this and converts it to:
```json
{"detail": "Internal Server Error"}
```

The HTTP status code is **500**. The client gets zero information about what went wrong.

### The Fix

```python
# ✅ FIXED CODE
flat_update_payload = {}
if request.flat_details:  # Check before accessing!
    flat_update_payload = request.flat_details.model_dump(exclude_unset=True, exclude={'occupied'})
```

**Why `exclude_unset=True`?** This is the correct pattern for partial updates (PATCH semantics):

```python
# Without exclude_unset=True:
class FlatUpdate(BaseModel):
    address: Optional[str] = None
    bedrooms: Optional[int] = None

# If client sends: {"bedrooms": 3}
# model_dump() returns: {"address": None, "bedrooms": 3}  ← address becomes None!

# With exclude_unset=True:
# model_dump(exclude_unset=True) returns: {"bedrooms": 3}  ← only what was actually sent
```

This prevents overwriting existing data with `None` when the client only sends a subset of fields.

---

## 9. The Action-Based PATCH Pattern

### Why Action-Based Instead of Multiple Endpoints?

**Option A: Multiple Endpoints**
```
POST /flats/{uuid}/tenant      → add tenant
PATCH /flats/{uuid}/tenant     → update tenant
DELETE /flats/{uuid}/tenant    → remove tenant
PATCH /flats/{uuid}            → update flat details only
```

**Option B: Action-Based Single PATCH** (what we chose)
```
PATCH /flats/{uuid}  body: { action: "ADD_TENANT", tenant_data: {...} }
PATCH /flats/{uuid}  body: { action: "REMOVE_TENANT" }
PATCH /flats/{uuid}  body: { action: "UPDATE_TENANT", tenant_data: {...} }
PATCH /flats/{uuid}  body: { action: "UPDATE_FLAT_ONLY", flat_details: {...} }
```

**Why Option B for this use case:** The flat and its tenant are tightly coupled. When you add a tenant, you also update `flat.occupied` and `flat.tenant_uuid`. Having a single endpoint that does all of this as one "transaction" is cleaner than coordinating multiple separate API calls from the frontend.

### Full Action Dispatch Implementation

```python
@router.patch("/{flat_uuid}", response_model=FlatResponse)
async def update_flat_details(flat_uuid: str, request: FlatEditRequest, db: Client = Depends(get_db)):

    # 1. Fetch current state (always needed regardless of action)
    current_flat_resp = db.table("flats").select("*").eq("uuid", flat_uuid).execute()
    if not current_flat_resp.data:
        raise HTTPException(status_code=404, detail="Flat not found")
    current_flat = current_flat_resp.data[0]
    current_tenant_uuid = current_flat.get("tenant_uuid")

    # 2. Pre-validate action vs current state
    if request.action == 'ADD_TENANT':
        if current_tenant_uuid:
            raise HTTPException(status_code=400, detail="Cannot add tenant: Flat is already occupied")
        if not request.tenant_data:
            raise HTTPException(status_code=400, detail="tenant_data required for ADD_TENANT")

    elif request.action == 'REMOVE_TENANT':
        if not current_tenant_uuid:
            raise HTTPException(status_code=400, detail="Cannot remove tenant: Flat is already vacant")

    elif request.action == 'UPDATE_TENANT':
        if not current_tenant_uuid:
            raise HTTPException(status_code=400, detail="Cannot update tenant: Flat is vacant")
        if not request.tenant_data:
            raise HTTPException(status_code=400, detail="tenant_data required for UPDATE_TENANT")

    # 3. Execute tenant operation
    new_tenant_uuid = current_tenant_uuid

    if request.action == 'ADD_TENANT':
        tenant_res = db.table("tenants").insert({
            "name": request.tenant_data.name,
            "phone": request.tenant_data.phone,
            "flat_uuid": flat_uuid
        }).execute()
        if not tenant_res.data:
            raise HTTPException(status_code=500, detail="Failed to create tenant")
        new_tenant_uuid = tenant_res.data[0]['uuid']

    elif request.action == 'REMOVE_TENANT':
        db.table("tenants").delete().eq("uuid", current_tenant_uuid).execute()
        new_tenant_uuid = None

    elif request.action == 'UPDATE_TENANT':
        db.table("tenants").update({
            "name": request.tenant_data.name,
            "phone": request.tenant_data.phone
        }).eq("uuid", current_tenant_uuid).execute()

    # 4. Execute flat update
    flat_update_payload = {}
    if request.flat_details:
        flat_update_payload = request.flat_details.model_dump(exclude_unset=True, exclude={'occupied'})

    if new_tenant_uuid != current_tenant_uuid:
        flat_update_payload['tenant_uuid'] = new_tenant_uuid  # Can be None (removing) or UUID (adding)

    if flat_update_payload:
        update_res = db.table("flats").update(flat_update_payload).eq("uuid", flat_uuid).execute()
        if not update_res.data:
            raise HTTPException(status_code=500, detail="Failed to update flat")
        final_flat = update_res.data[0]
    else:
        final_flat = current_flat

    # 5. Fetch final tenant for response
    tenant_info = None
    if final_flat.get('tenant_uuid'):
        t_res = db.table("tenants").select("*").eq("uuid", final_flat['tenant_uuid']).execute()
        if t_res.data:
            tenant_info = t_res.data[0]

    # 6. Return with strict schema validation
    return FlatResponse.model_validate({**final_flat, "tenant": tenant_info})
```

---

## 10. `FlatResponse.model_validate()` — Why Strict Schema Return Matters

### The Problem with Returning Raw Dicts

```python
# ❌ BAD — Returns raw dict, bypasses schema validation
return {**final_flat, "tenant": tenant_info}

# What can go wrong:
# - Schema says tenant_uuid is UUID but DB returns str → silent mismatch
# - Schema says occupied is bool but DB returns None → downstream crashes
# - Extra fields from DB leak into response (e.g., internal DB metadata)
```

### The Fix — `model_validate()`

```python
# ✅ GOOD — Strict schema enforcement
return FlatResponse.model_validate({**final_flat, "tenant": tenant_info})
```

`model_validate()` is Pydantic v2's replacement for `from_orm()` / `parse_obj()`. It:
1. Validates all field types
2. Applies all field validators
3. Raises `ValidationError` immediately if data doesn't match schema
4. Strips extra fields not in the schema
5. Fills in defaults for missing optional fields

**Why this saved us:** When tenant_uuid was being returned as a raw string from the DB but the schema declared it as `Optional[UUID]`, Pydantic v2 auto-coerces it. If the field was completely malformed, it would raise at this point rather than silently returning bad data to the frontend.

---

## 11. The Inconsistent Occupancy Logic Bug

### The Problem

Two different places in the UI were checking different things to determine if a flat was occupied:

```javascript
// In FlatsListPage.jsx (Flat cards):
const isOccupied = flat.occupied;           // Boolean field in DB

// In FlatDetailModal.jsx (Flat detail view):
const isOccupied = flat.tenant !== null;    // Presence of nested tenant object
```

**Why this broke:** The `flat.occupied` boolean can get out of sync with reality. If a tenant was removed but the DB update only cleared `tenant_uuid` without also setting `occupied = false`, then:
- The flat list shows "Occupied" (because `occupied` is still `true`)
- The detail modal shows "Available" (because `tenant` object is null)

### The Fix — Single Source of Truth

```javascript
// ✅ ONE consistent check everywhere in the codebase
const isOccupied = !!flat.tenant_uuid;
```

**Why `tenant_uuid` is the reliable source:**
- It's a foreign key — if there's a tenant_uuid, a tenant exists
- It's updated atomically with the tenant creation/deletion
- It's immune to out-of-sync boolean drift
- `!!` converts UUID string to boolean cleanly (`!!null → false`, `!!"uuid-string" → true`)

**How to enforce this in the backend too:**
```python
# Always derive occupied from tenant_uuid, never store it independently
flat_update_payload['tenant_uuid'] = new_tenant_uuid
# The frontend derives: isOccupied = !!flat.tenant_uuid
# No need to track the occupied boolean separately
```

---

## 12. Optimistic UI Updates

### The Problem with Naive Refetching

```javascript
// ❌ BAD APPROACH — Refetch the entire list after edit
const handleFlatUpdate = async (uuid, data) => {
    await updateFlat(uuid, data);
    await fetchAllFlats();  // Slow! Re-fetches all flats from server
};
```

**Problems:**
- Slow: user sees a loading state after every edit
- Wasteful: fetches all data when only one record changed
- Jarring UX: the list flickers on every update

### The Fix — Update Local State In-Place

```javascript
// ✅ GOOD APPROACH — Update local state, use what the server returns
const handleFlatUpdate = async (uuid, actionData) => {
    // API returns the complete updated flat object
    const updatedFlat = await updateFlat(uuid, actionData);

    // Replace the one changed flat in our state array
    setProperties(prev => prev.map(p =>
        p.uuid === uuid ? updatedFlat : p
    ));

    // No full refetch needed!
};
```

**The key requirement:** The backend MUST return the complete updated object. If it only returns `{ success: true }`, you can't do this.

```python
# Backend — always return the full updated record
return FlatResponse.model_validate({**final_flat, "tenant": tenant_info})
#        ↑ This includes all fields the frontend needs
```

---

## 13. Windows Debugging Errors You'll Hit

### Error: UnicodeEncodeError on Windows Console

**Exact error message:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2705' in position 0:
character maps to <undefined>
```

**When it happens:** You use emojis (✅, ❌, 🚀) in `print()` statements. Windows cmd/PowerShell uses legacy `cp1252` encoding by default, which can't represent Unicode characters above U+00FF.

**Quick fix (for scripts/tests):** Remove emojis from print statements.

**Proper fix (persistent):**
```bash
# Set environment variable before running Python
set PYTHONIOENCODING=utf-8
python your_script.py

# Or in PowerShell
$env:PYTHONIOENCODING = "utf-8"
python your_script.py
```

**Or in Python code itself:**
```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

### Error: uvicorn Module Not Found

**Exact error message:**
```
'uvicorn' is not recognized as an internal or external command
```
or
```
ModuleNotFoundError: No module named 'uvicorn'
```

**Root Cause:** You installed packages into a virtual environment (`.venv`) but your shell is using the global Python. `uvicorn` only exists inside the venv.

**Diagnosis:**
```bash
# Check if you're in the venv (should show venv path)
where python   # Windows cmd
# or
which python   # Git Bash
```

**Fix 1 — Activate the venv:**
```bash
# Windows cmd
.venv\Scripts\activate

# Git Bash on Windows
source .venv/Scripts/activate

# Then run normally
uvicorn app.main:app --reload
```

**Fix 2 — Use explicit venv path (without activating):**
```bash
.venv\Scripts\python -m uvicorn app.main:app --reload
```

**Why Fix 2 works even without activation:** It bypasses the PATH entirely and directly invokes the venv's Python binary, which has all venv-installed packages available.

### Error: Connection Refused (WinError 10061)

**Exact error message:**
```
[WinError 10061] No connection could be made because the target machine actively refused it
```

**When it happens:** You try to connect to `localhost:8000` but the FastAPI server isn't running.

**Diagnosis checklist:**
1. Is uvicorn running? Check your terminal for `Uvicorn running on http://127.0.0.1:8000`
2. Did it crash? Scroll up in the terminal for a Python traceback
3. Did you start it on a different port? Check your start command
4. Is something else using port 8000?

```bash
# Check what's on port 8000 (Windows)
netstat -ano | findstr :8000
# If something is there, either kill it or use a different port:
uvicorn app.main:app --reload --port 8001
```

---

## 14. Common Mistakes Checklist

| Mistake | Symptom | Fix |
|---------|---------|-----|
| `python-multipart` not installed | `RuntimeError: Form data requires "python-multipart"` | `pip install python-multipart` |
| Setting `Content-Type` manually for FormData | Server gets empty body or boundary mismatch | Remove the `Content-Type` header |
| Using JSON body + `Form()` in same route | FastAPI startup error or 422 | Use ALL `Form()` or ALL JSON body, not mixed |
| Using original filename for uploads | Collision, path traversal risk | Always use `uuid4()` for the storage filename |
| No cleanup on upload failure | Orphaned files in storage | Track `uploaded_filename` and delete on any exception |
| Accessing `.model_dump()` on None | 500 Internal Server Error | Always check `if request.flat_details:` first |
| Checking `flat.occupied` boolean for occupancy | Stale data, inconsistent UI | Use `!!flat.tenant_uuid` as the single source of truth |
| Not using `exclude_unset=True` on PATCH | Overwrites optional fields with None | Always use `model_dump(exclude_unset=True)` for PATCH |
| Returning raw dicts instead of `model_validate()` | Silent type mismatches, extra fields leaking | Return `FlatResponse.model_validate(data)` |

---

## 15. Implementation Checklist

### Add Property Feature
- [ ] Install `python-multipart` and add to `requirements.txt`
- [ ] Create "Property Pics" bucket in Supabase Storage (set as Public)
- [ ] Declare route parameters with `Form(...)` and `File(None)` (not a Pydantic body model)
- [ ] Validate file type from `image.content_type`
- [ ] Validate file size after `await image.read()`
- [ ] Use `uuid4()` for storage filename (never original filename)
- [ ] Track `uploaded_filename` variable before upload for cleanup
- [ ] Check for duplicate flat_number BEFORE DB insert (with cleanup if found)
- [ ] Implement cleanup in all exception branches
- [ ] Return complete flat + nested tenant in response

### Flat Edit Feature
- [ ] Create `FlatEditRequest` schema with `Literal` action field
- [ ] Validate action vs current state (can't add tenant if occupied, etc.)
- [ ] Use `if request.flat_details:` guard before `.model_dump()`
- [ ] Use `model_dump(exclude_unset=True)` for partial updates
- [ ] Return `FlatResponse.model_validate({...})` for strict output validation
- [ ] Replace all `flat.occupied` checks with `!!flat.tenant_uuid` in frontend

### Frontend
- [ ] Use `FormData` API, NOT JSON for multipart requests
- [ ] Do NOT set `Content-Type` header when sending `FormData`
- [ ] Update local state with the returned updated object (optimistic UI)
- [ ] Show image preview using `URL.createObjectURL()` before upload

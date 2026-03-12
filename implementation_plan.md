# Add Tenant Email and Document Upload

This plan outlines the changes required to add an email field and document upload functionality to the tenant management module, controlled by unit-level feature settings.

## User Review Required
- **Supabase Bucket**: A new Supabase storage bucket named `Tenant_docs` must be created manually in your Supabase dashboard prior to testing.
- **SQL Query Execution**: The following SQL must be executed in your Supabase SQL Editor to alter the [tenants](file:///c:/Users/BIT/Coding/Tenant_management_MVP/backend/app/routes/tenants.py#249-361) table:
```sql
ALTER TABLE tenants
ADD COLUMN email TEXT,
ADD COLUMN document_urls TEXT[] DEFAULT '{}';
```

## Proposed Changes

### Backend - Database Schema
- Provide the SQL query (as seen above) to add `email` and `document_urls` to the [tenants](file:///c:/Users/BIT/Coding/Tenant_management_MVP/backend/app/routes/tenants.py#249-361) table.

---

### Backend - Schemas
#### [MODIFY] [tenant.py](file:///c:/Users/BIT/Coding/Tenant_management_MVP/backend/app/schemas/tenant.py)
- **TenantBase / TenantCreate / TenantUpdate / TenantResponse**: Add `email: Optional[str] = None`. Note: specifically ensure it is in [TenantUpdate](file:///c:/Users/BIT/Coding/Tenant_management_MVP/backend/app/schemas/tenant.py#24-34).
- **TenantCreate / TenantUpdate / TenantResponse**: Add `document_urls: Optional[list[str]] = []`.
- **TenantResponse**: Add `tenant_documents_enabled: Optional[bool] = None` to pass the feature flag state to the frontend.

---

### Backend - Routes
#### [MODIFY] [tenants.py](file:///c:/Users/BIT/Coding/Tenant_management_MVP/backend/app/routes/tenants.py)
- In [get_all_tenants](file:///c:/Users/BIT/Coding/Tenant_management_MVP/backend/app/routes/tenants.py#249-361), modify the feature flag fetching logic to also query for `"tenant_documents"` alongside `"tenant_details"`.
- Assign `t["tenant_documents_enabled"]` properly when building the enriched response list.

#### [MODIFY] [upload.py](file:///c:/Users/BIT/Coding/Tenant_management_MVP/backend/app/routes/upload.py)
- Ensure the bucket selection logic checks `entity_type`. If `entity_type == "tenant_document"`, use `BUCKET_NAME = "Tenant_docs"`, otherwise default to `"Property Pics"`.

---

### Frontend - React Components
#### [MODIFY] [TenantProfile.jsx](file:///c:/Users/BIT/Coding/Tenant_management_MVP/frontend/src/components/TenantProfile.jsx)
- **Email Field**: Under the "Contact" or top profile section, display and edit the email. It will be protected from view/edit if `tenant_details_enabled === false`.
- **Documents Section**: Add a new section for documents.
  - Check `tenant.tenant_documents_enabled !== false` before showing this section (default is `false` as per [backend/app/core/features.py](file:///c:/Users/BIT/Coding/Tenant_management_MVP/backend/app/core/features.py)).
  - Read-only mode: Render links/buttons to view the URLs in `tenant.document_urls`. 
  - Edit mode: Provide a file input that uses the upload API with `entity_type="tenant_document"` to upload to `Tenant_docs` and updates the `form.document_urls` array.

## Verification Plan

### Automated Tests
- N/A for this change as there are no test suites present for these routes. Build checks and type safety via Pydantic will be verified locally.

### Manual Verification
1. Run the backend and frontend locally.
2. Ensure the `Tenant_docs` bucket exists and the SQL migrations have run.
3. On the frontend Settings page, enable "Tenant Documents" for a unit or property.
4. Go to the Tenant Management page, select a tenant, and verify the Email field can be edited and saved.
5. In Edit mode, attempt to upload a document (PDF or image). Wait for the upload, then click save.
6. Verify the document appears in the read-only view and can be opened as a public URL.

# Implementation Plan: SMS Workflow Page

## Goal Description
Allow the property manager to manually send SMS messages to selected tenants. The feature will use the existing Twilio implementation already configured in the system. This involves creating a new frontend page with tenant selection and message editing, and a backend endpoint to broadcast the message using Twilio.

## Proposed Changes

### Backend

#### [NEW] `backend/app/schemas/workflow.py`
Create Pydantic models for the request payload and response to ensure data validity:
- `SmsWorkflowRequest`:
  - `tenant_ids`: `List[UUID]` — uses tenant UUIDs as stable identifiers (matching the rest of the API)
  - `message`: String (min length 1)
- `SmsResult`:
  - `tenant_id`: UUID
  - `success`: bool
  - `sid`: Optional[str] — Twilio message SID if sent successfully, else None
- `SmsWorkflowResponse`:
  - `results`: `List[SmsResult]`

#### [NEW] `backend/app/routes/workflow.py`
Create the actual API endpoint that processes the SMS workflow request:
- `POST /workflow/send-sms`
- Accepts `SmsWorkflowRequest`, returns `SmsWorkflowResponse`
- Iterates through the provided `tenant_ids`, looks up each tenant's phone number from the database by UUID, and uses [get_twilio_client().send_sms(to=phone, message=message)](file:///c:/Users/BIT/Coding/Tenant_management_MVP/backend/app/integrations/twilio_client.py#60-66).
- Implements logging for success/failure per tenant.
- Each result entry contains `{ tenant_id, success, sid }` regardless of whether the send succeeded or failed.

#### [MODIFY] [backend/app/main.py](file:///c:/Users/BIT/Coding/Tenant_management_MVP/backend/app/main.py)
- Import and include the new `workflow.router` into the FastAPI app.

---

### Frontend

#### [MODIFY] [frontend/src/services/apiService.js](file:///c:/Users/BIT/Coding/Tenant_management_MVP/frontend/src/services/apiService.js)
- Add a new function `sendWorkflowSms(tenantUuids, message)` to issue a POST request to `/workflow/send-sms`.
- `tenantUuids` is an array of UUID strings (tenant `uuid` field, not `id`).
- Returns the full `SmsWorkflowResponse` body (`{ results: [{tenant_id, success, sid}] }`).

#### [NEW] `frontend/src/components/SmsWorkflow.jsx`
Create a new comprehensive UI component covering:
- **Tenant List/Table**: Fetched using existing `fetchTenants` from `apiService.js`. Display the tenant's integer `id` as the visible row identifier (for human readability), but track selection by `uuid`.
- **Selection State**: A list of selected tenant UUIDs updated via individual checkboxes and a "Select All" toggle.
- **Message Editor**: Textarea for composing the message.
- **Action Button**: "Send SMS" button that is disabled if no tenants are selected or the message is empty.
- **UI Feedback**: After the request completes, display a banner at the top of the page:
  - **All succeeded**: green success box — "SMS sent successfully to X tenant(s)."
  - **Any failed**: red error box — "Failed to send SMS to X tenant(s)." (partial failure also shows red).

#### [MODIFY] [frontend/src/components/Sidebar.jsx](file:///c:/Users/BIT/Coding/Tenant_management_MVP/frontend/src/components/Sidebar.jsx)
- Import `MessageSquareMore` from `lucide-react`.
- Add `{ id: 'workflow', icon: MessageSquareMore, label: 'SMS Workflow' }` to the `navItems` array.

#### [MODIFY] [frontend/src/App.jsx](file:///c:/Users/BIT/Coding/Tenant_management_MVP/frontend/src/App.jsx)
- Import `SmsWorkflow` component.
- Add `{currentView === 'workflow' && <SmsWorkflow />}` **outside** the `loading && complaints.length === 0` guard block, so the SMS Workflow page is always reachable regardless of complaint loading state.

## Verification Plan

### Automated/Local Tests
- **Backend API Validation(ask before runningbecause I will be running the backend server manually on bash so you don't have to run it on your terminal)**: Ensure that the endpoint returns a `422 Unprocessable Entity` when an empty list of tenants or empty message string is sent via Swagger UI (`http://localhost:8000/docs`).

### Manual Verification
- **Frontend Navigation**: Click on the new "SMS Workflow" sidebar item to confirm the component mounts without errors.
- **Selection Feature Check**: Select individual tenants, toggle "Select All" on and off, and verify the correct number of tenants is reported to be selected.
- **Validation Check**: Confirm that the "Send SMS" button is blocked or shows an error if the message field is empty.
- **End-to-End Send Test**:
  1. Add a test tenant with the user's phone number or a designated testing number.
  2. Select only that test tenant in the SMS Workflow page.
  3. Enter a test message.
  4. Click "Send SMS".
  5. Check UI for success feedback.
  6. Check backend server logs for the successfully sent Twilio message SID.
  7. Verify receiving the actual SMS on the test phone.

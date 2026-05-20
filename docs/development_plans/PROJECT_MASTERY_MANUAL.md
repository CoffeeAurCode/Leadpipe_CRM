# INTERNAL ENGINEERING BIBLE: TENANT MANAGEMENT MVP

**CONFIDENTIAL INTERNAL DOCUMENT**  
**Role:** Principal Engineer / Technical Architect  
**Objective:** Transform junior developers into senior systems thinkers capable of scaling this platform to enterprise scale.

This is NOT a summary document. This is your definitive mastery manual. If you read this, assimilate it, and practice its exercises, you will fully master this system. Stop copying and pasting blindly; start thinking in systems.

---

## 1. Project Vision & System Overview

### What problem this system solves
Property managers oversee hundreds of units. Tenants report maintenance issues constantly via phone. Historically, these calls are missed, forgotten, or poorly logged. This system replaces the human receptionist with an AI voice agent (Vapi + Groq) that talks to the tenant, parses their exact issue safely, books an appointment, and pushes it real-time to a digital manager dashboard.

### Real-world equivalent systems
*   **Zendesk Voice / Intercom:** Automated customer support ingestion.
*   **AppFolio / Buildium:** Standard property management suites, though usually lacking voice-native AI ingestion.

### End-to-End Flow Walkthrough (Step-by-Step)
1.  **Ingestion:** Tenant calls the Vapi phone number.
2.  **Interaction:** Vapi STT (Speech-to-Text) translates audio to text. Vapi's internal LLM handles the conversation.
3.  **Intent Confirmation:** The tenant explicitly confirms they want to submit a complaint (e.g., "Yes, log the pipe issue").
4.  **Edge Trigger:** Vapi executes the `submit_complaint` tool, firing an HTTP POST to our backend `/voice/webhook`.
5.  **Data Extraction:** Our backend receives the transcript. It sends it to Groq (Llama 3.1) to extract structured JSON (`flat_number`, `category`, `priority`, `description`).
6.  **Idempotency & Persistence:** The backend checks the uniquely generated `call_id` against the `call_logs` table to ensure we do not create duplicate complaints. It then writes the complaint to the Supabase PostgreSQL database.
7.  **Asynchronous Escalation:** The backend spawns a non-blocking background task to send an email to the property manager via SendGrid.
8.  **UI Consumption:** The React SPA (Single Page Application) dashboard, which polls the database, fetches the new complaint and renders it in the Bento Grid UI.

### Complete Request Lifecycle Breakdown
*   `Client (Vapi)` -> `FastAPI CORSMiddleware` (Headers Validation) -> `routes/voice.py (voice_webhook)` -> `Payload JSON Parsing` -> `Event Filtering (tool-calls)` -> `ai/extractor.py (Groq LLM Network Call)` -> `Idempotency Check (DB Select)` -> `HTTP POST to self /complaints (Anti-Pattern)` -> `Supabase DB Insert` -> `FastAPI BackgroundTasks` -> `HTTP 200 OK to Vapi`.

### Architecture Diagram

```ascii
+-----------------+       +--------------------+       +-------------------+
|  Tenant Phone   | ----> |  Vapi AI (Voice)   | ----> |  Groq (Llama 3.1) |
+-----------------+       +--------------------+       +-------------------+
                                   | (Webhook POST)             ^ (Transcript via API)
                                   v                            |
+-------------------------------------------------------------------------+
|                              FastAPI Backend                            |
|                                                                         |
|  +----------------+    +------------------+    +---------------------+  |
|  | routes/voice.py| -> | ai/extractor.py  | -> | routes/complaints.py|  |
|  +----------------+    +------------------+    +---------------------+  |
|          | (Background Task)                             |              |
|          v                                               v              |
|  +-------------------+                           +-------------------+  |
|  | integrations/email|                           |   Supabase Client |  |
|  +-------------------+                           +-------------------+  |
+-------------------------------------------------------------------------+
           |                                               |
           v                                               v
+-----------------+                              +-------------------+
|  SendGrid APIs  |                              | PostgreSQL DB     |
+-----------------+                              +-------------------+
                                                           ^
                                                           | (REST GET)
                                                 +-------------------+
                                                 | React Dashboard   |
                                                 +-------------------+
```

### Data Flow Diagram
`Voice Transcript` -> `LLM Extraction Object` -> `Complaint Pydantic Schema` -> `Supabase Dict` -> `PostgreSQL Row` -> `React State Object` -> `DOM Render`.

---

## 2. Technology Stack Deep Breakdown

### A. FastAPI (Python)
*   **What it is:** A modern, fast (high-performance), web framework for building APIs with Python 3.8+ based on standard Python type hints.
*   **Why it is used here:** Native `async/await` support is mandatory for I/O heavy operations (calling Vapi, Groq, Supabase, SendGrid). It auto-generates OpenAPI docs.
*   **Internals:** Runs on Starlette (ASGI toolkit) and Pydantic (data validation). It leverages the Python event loop to switch contexts while waiting for network responses.
*   **How this project uses it:** As the core router and request orchestrator.
*   **Beginner Misunderstanding:** Confusing `def` vs `async def`. If you put a synchronous blocking call (like `requests.get`) inside an `async def` route without `await`, you freeze the ENTIRE server. All concurrent users stop.
*   **Advanced Internals:** FastAPI Dependency Injection (`Depends()`). It caches dependencies per request.
*   **Docs:** [FastAPI Official Docs](https://fastapi.tiangolo.com/)

### B. Supabase (PostgreSQL) via HTTP Client
*   **What it is:** A Backend-as-a-Service built on top of PostgreSQL. Provides a REST API (PostgREST) directly over the database.
*   **Why it is used here:** Zero configuration needed for setting up connection pools or writing raw SQL for basic CRUD during the MVP phase.
*   **Internals:** Transforms HTTP GET/POST/PATCH requests into parameterized SQL queries executed against Postgres.
*   **How this project uses it:** The `supabase-py` client is used inside route handlers (`db.table('complaints').insert()`).
*   **Beginner Misunderstanding:** Thinking this is an ORM like SQLAlchemy. It is NOT. It is an HTTP client wrapping a REST API. You lack strict type safety at compile time.
*   **Advanced Internals:** Row Level Security (RLS) in Postgres, which PostgREST respects based on the JWT sent (though this project bypasses it via service keys).
*   **Docs:** [Supabase Python Client](https://supabase.com/docs/reference/python/introduction)

### C. React & Vite
*   **What it is:** React is a UI library based on a Virtual DOM. Vite is an ultra-fast build tool leveraging native ES Modules.
*   **Why it is used here:** Industry standard for dynamic SPAs. Vite provides sub-second hot-module replacement (HMR), making frontend design iteration incredibly fast.
*   **Internals:** React reconciles changes in state against a Virtual DOM, computes the diff, and paints only the changed HTML nodes to the real DOM.
*   **How this project uses it:** A dashboard displaying a Bento Grid layout of complaints, polling the FastAPI backend.
*   **Beginner Misunderstanding:** Mutating state directly (`complaints.push(new_complaint)`) instead of immutably (`setComplaints([...complaints, new_complaint])`). React will NOT re-render if you mutate directly because the object reference identifier doesn't change.
*   **Docs:** [React.dev](https://react.dev/) | [Vite](https://vitejs.dev/)

---

## 3. Backend Mastery Section

### A. Routing Layer (`routes/`)
*   **Structure:** Distinct files for domain entities (`complaints.py`, `voice.py`, `flats.py`). Included in `main.py` via `APIRouter()`.
*   **Validation Flow:** `Request JSON` -> `Pydantic Schema (ComplaintCreate)` -> `If Invalid: 422 Unprocessable Entity` -> `Route Handler`.
*   **Response Models:** Routes strictly define `response_model=ComplaintResponse`. This filters outward data, preventing password hashes or internal IDs from leaking to the frontend.
*   **Error Patterns:** Wrapped in try/except blocks throwing `HTTPException(status_code=500)`.
*   **Crucial Improvement Required:** Stop catching `Exception as e` and throwing 500s. We need domain-specific exceptions (e.g., `TenantNotFoundError` -> HTTP 404, `DuplicateCallError` -> HTTP 409).

### B. Business Logic Layer
*   **Separation of Concerns Analysis:** **FAILING.** Currently, business rules (like checking if a flat exists before creating a complaint) live directly inside `routes/complaints.py`.
*   **Where Business Rules Live:** They are coupled to the HTTP transport layer.
*   **Anti-pattern:** The "Fat Controller". `voice_webhook` is 400 lines long. It handles JSON parsing, AI extraction, idempotency checking, database insertion, and background task orchestration.
*   **Refactoring Possibility:** Create `app/services/complaint_service.py`. 
    ```python
    # Refactored Service Example
    class ComplaintService:
        def __init__(self, db: Client):
            self.db = db
            
        def process_voice_complaint(self, transcript: str, call_id: str) -> Complaint:
            if self._is_duplicate(call_id):
                return self._get_existing(call_id)
            data = extractor.extract(transcript)
            return self._create_in_db(data)
    ```

### C. Database Layer (`db/models.py`)
*   **Schema Explanation:** Defines physical structures for Users, Units/Flats, Tenants, Complaints, and CallLogs.
*   **Table Relationships:**
    *   `Tenant` (1) -> (N) `Complaint`
    *   `CallLog` (1) -> (1) `Complaint`
    *   `Unit/Flat` (1) -> (N) `Tenant`
*   **Index Reasoning:** No explicit indexes are defined in `models.py` aside from primary keys. If the `call_logs.call_id` and `complaints.created_at` fields are queried frequently (they are), they *must* be indexed in PostgreSQL or the webhook latency will spike linearly as data grows.
*   **Query Patterns:** `db.table(...).select(...).eq(...)`.
*   **Transactions:** **SEVERE RISK.** Because the project uses Supabase PostgREST Client, you do not have atomic transaction blocks (e.g., `BEGIN; INSERT INTO complaints; INSERT INTO appointments; COMMIT;`). If the complaint inserts, but the appointment HTTP call drops, you have corrupted orphaned data.
*   **Data Integrity Risks:** Because of the lack of `BEGIN/COMMIT` blocks via the REST client, relational integrity relies purely on the hope that sequential HTTP calls succeed.

**ASCII ER Diagram:**
```ascii
[flats]
  id (PK)
  flat_number
  |
  | 1:N
  v
[tenants]
  id (PK)
  phone
  flat_uuid (FK)
  |
  | 1:N
  v
[complaints]
  id (PK)
  tenant_uuid (FK)
  category
  status
  <------ 1:1 -----[call_logs]
                     call_id (UQ)
                     transcript
                     complaint_id (FK)
```

**How to debug DB issues:**
If data is missing, grab the `call_id` from the Vapi dashboard. Run:
`SELECT * FROM call_logs WHERE call_id = 'your_call_id';`
Check the `complaint_status`. If it says "incomplete", Groq failed to extract the required fields.

### D. Integrations

#### 1. Vapi (Voice Webhooks)
*   **How it works:** Vapi streams audio to LLMs, determines tool execution, and sends massive JSON payloads to `/voice/webhook`.
*   **Failure Cases:** Vapi sends a webhook, your server takes 12 seconds to respond. Vapi times out, assuming failure, and retries. Your server finishes the first request, creates a complaint, then receives the retry and creates a SECOND complaint.
*   **Idempotency Explanation:** We solve the failure case via Idempotency Keys. The `call_id` acts as out lock. We query `call_logs` first. If `call_id` exists, we immediately return 200 OK without processing to break the retry loop.
*   **Production Hardening:** You must verify the `x-vapi-secret` header. Currently, anyone can `POST /voice/webhook` via curl and inject fake complaints into your system.

#### 2. SendGrid (Email)
*   **How it works:** `EmailClient` hits SendGrid's `/v3/mail/send` REST API to dispatch templates.
*   **Failure Cases:** API Key rotated, rate limits exceeded, SendGrid DNS down.
*   **Retry Logic Design:** Currently none. If it fails, `logger.error` fires, but the email is lost. 
*   **Production Hardening:** Push email tasks into a durable queue (Celery + Redis or RabbitMQ) that automatically retries exponentially on failure.

---

## 4. Frontend Mastery Section

### Component Architecture Breakdown
The UI heavily utilizes a **Bento Grid** component architecture.
*   `App.jsx` (Root layout, State owner, Data fetcher)
*   `Sidebar.jsx` (Navigation UI)
*   `BentoDashboard.jsx` (Orchestrator for the grid)
    *   `QuickFilters.jsx` (Updates state)
    *   `CompactStatsGrid.jsx` (Calculates derived state)
    *   `CompactCalendar.jsx`
    *   `CompactComplaintCard.jsx` (Dumb presentation component)

### State Management Logic
State is hoisted to `App.jsx` (`complaints`, `loading`, `error`). Functions like `handleComplaintUpdate` are passed down as props 4-levels deep (Prop Drilling). 

### Data Fetching Pattern
Using native `fetch()` heavily tied to React's `useEffect()`. It mounts -> loads -> sets interval data fetching (polling).

### Re-Render Reasoning & Risks
**CRITICAL FLAW:** In `App.jsx`:
```javascript
const interval = setInterval(loadComplaints, 30000);
```
`loadComplaints` calls `setComplaints(data)`, creating a completely new array reference. React sees a new reference and completely destroys and re-renders the DOM tree for the dashboard every 30 seconds. If a user has a modal open or is copying text, it might abruptly close or glitch.

### Refactor to Scalable Structure
Throw away `setInterval`. Install `@tanstack/react-query`.
```javascript
// The Senior Way
const { data: complaints } = useQuery({
  queryKey: ['complaints'],
  queryFn: fetchComplaints,
  refetchInterval: 30000,
  staleTime: 10000,
});
```
React Query caches the data. It fetches in the background. It compares the old data with the new data mathematically, and only triggers a React re-render for the specific rows that changed.

---

## 5. Debugging & Failure Playbook

### Scenario A: The 500 Error
**Symptom:** Operations failing with HTTP 500 Internal Server Error.
**Strategy:**
1.  Check the FastAPI console output. Look for the Traceback.
2.  Did it occur in a route? Check the physical Supabase constraints. Did you try to insert a `flat_number` without mapping it to a `flat_uuid`?
3.  **To Fix:** Add `import traceback; traceback.print_exc()` in your generic exception catchers temporarily, or better, implement structured JSON logging with error stack traces.

### Scenario B: Webhook Issue / The Ghost Caller
**Symptom:** Manager claims tenant called, but nothing is on the dashboard.
**Strategy:**
1.  Check Vapi Dashboard -> Call Logs. Look at the Function Calls. Did Vapi execute `submit_complaint`?
2.  If Yes, obtain the `call_id`.
3.  Connect to Postgres (Supabase SQL Editor): `SELECT * FROM call_logs WHERE call_id = '<id>';`
4.  If it's there but `status`=incomplete, the AI extraction aborted due to missing details.
5.  If it's NOT there, your backend never received the webhook. Check your Cloudflare/Ngrok/Render logs for dropped connections.

### Scenario C: Stale State Issues (Frontend)
**Symptom:** Manager updates a complaint to "Resolved", it flashes "Resolved", then reverts back to "Pending" 10 seconds later, then goes back to "Resolved" 20 seconds later.
**Reason:** Race condition between optimistic UI updates and the 30-second polling interval. The 30-second poll fetched old data before the DB committed the patch.
**Fix:** In `handleComplaintUpdate`, use React Query to explicitly invalidate the cache or mutate the cache directly, rather than relying on manual state merging.

---

## 6. Testing Mastery (What to Build)

### Current Test Coverage
**0%.** The project relies entirely on manual end-to-end webhook execution to verify. This is unacceptable for a Staff Engineer.

### Missing Tests & Setup
You must install `pytest` and `httpx`.
Create `backend/tests/`.

### 1. Unit Testing Strategy (Logic & AI)
Test pure Python functions without an internet connection.
```python
# tests/test_extractor.py
from app.ai.extractor import extract_fields

def test_flat_extraction_priority():
    # Tests the Regex logic bypasses pure digits if alphanumeric exists
    assert _extract_flat_number("I am in flat A-101 and my number is 999") == "A-101"
```

### 2. Integration Testing Strategy (Webhooks)
Mock the database, but test the FastAPI router logic.
Create a mock JSON payload that completely replicates a Vapi `tool-calls` event.
Send it via `TestClient`. Assert that the endpoint returns `200` and `complaint_created == True`.

### 3. API Contract Testing
Write a test that hits `GET /complaints` and runs Pydantic's `.model_validate()` against the response to ensure your schema matches your database exactly.

---

## 7. Production Engineering (How to Scale)

Right now, this codebase is an MVP. Here is the path to an Enterprise SLA.

### 1. The Database Architecture (Stop using HTTP for CRUD)
Replace `supabase-py` inside the FastAPI routes with `SQLAlchemy` (with `asyncpg`). 
*   **Why:** HTTP overhead adds ~50-100ms per database query. A persistent TCP connection via `asyncpg` adds ~1-3ms. You instantly increase your system throughput by 5000%.

### 2. Observability 
*   **Current:** `print("Reached here")`
*   **Upgrade:** Install DataDog or Sentry. Every request must be attached to a Trace ID. When a webhook fails, you need to open an APM UI and see a waterfall graph of exactly how many milliseconds the LLM took vs the DB insert.

### 3. Background Job Handling
*   **Current:** `BackgroundTasks.add_task(send_email)`
*   **Risk:** If the FastAPI server crashes/restarts 10 milliseconds after queueing the task, the task is destroyed in memory. The email never sends.
*   **Upgrade:** Use `Celery` with Redis architecture. If the server dies, the message remains safely in Redis until a worker comes back online to process it.

### Simulate Scaling:
*   **100 Users:** Works fine.
*   **10,000 Users:** The 30-second frontend polling kills the Supabase API limits. You get rate limited. Server crashes. **Fix:** Implement Server-Sent Events (SSE) or WebSockets. PUSH data to the frontend only when a complaint changes. Zero polling.
*   **1,000,000 Users:** Postgres write locks become an issue. You need a read-replica DB for the Managers to perform heavy `GET` aggregate queries, while the master DB only processes `INSERT` from webhooks.

---

## 8. Senior-Level Refactor Blueprint

### Phase 1 – Stabilize (Stop the Bleeding)
1.  Remove the `httpx.post("http://localhost:8000/complaints")` hack loopback inside `voice.py`.
2.  Write a simple internal python function `create_complaint_internal(data, call_id)` and call it directly.

### Phase 2 – Clean Architecture (Layering)
1.  Create `app/services/`
2.  Create `app/repositories/`
3.  Move ALL `db.table('...').execute()` calls into the repositories.
4.  Routes should now look like: 
    ```python
    @router.post("")
    async def create(data: ComplaintCreate, db: Session = Depends(get_db)):
        return ComplaintService.create(data, db)
    ```

### Phase 3 – Decouple & Modularize (The Frontend)
1.  Rip out `setInterval`.
2.  Install React Query.
3.  Replace all `useState` and `useEffect` fetching logic with `useQuery` hooks.
4.  Ensure no prop-drilling by leveraging Context API where necessary.

### Phase 4 – Scale & Harden (Production)
1.  Migrate completely from `supabase-py` REST to SQLAlchemy `asyncpg` direct connections to realize atomic transactions.
2.  Implement JWT-based authentication via Supabase Auth.
3.  Implement Vapi Webhook Secret validation securely.

---

## 9. Core Concepts Required to Truly Master This Project

### 1. HTTP Lifecycle & Webhooks
*   **Concept:** The internet works on Request -> Response. A Webhook is an inverse API (a server requesting your server).
*   **Application:** Vapi hits your `/voice/webhook`. You cannot wait for humans. The system must process payload immediately and automatically. 

### 2. Idempotency
*   **Concept:** An operation that produces the same result whether executed once or 10,000 times.
*   **Application:** Network requests fail. If Vapi sends the webhook twice, you must not charge the tenant twice, nor create two complaints. Our `call_logs.call_id` unique check guarantees this. This is the cornerstone of distributed systems.

### 3. ORMs vs REST Clients
*   **Concept:** Object-Relational Mappers translate Python classes to SQL. REST clients just construct HTTP requests.
*   **Application:** You are currently defining SQLAlchemy classes but using a REST client to fetch data. Understanding this mismatch is critical to diagnosing why you lack transaction support in this codebase.

### 4. Dependency Injection
*   **Concept:** Giving an object its instance variables (dependencies) from the outside, rather than it creating them itself.
*   **Application:** Inside FastAPI, `Depends(get_db)` injects the database client into the route. This allows you to easily inject a "Mock DB" during Pytest runs.

---

## 10. Learning Roadmap (12 Week Plan for Interns)

### Weeks 1-4: The Foundations of the Backend
*   **Study:** The FastAPI official tutorial (read it cover to cover).
*   **Read:** Cosmic Python (Architecture Patterns with Python) - specifically chapter 1 on Dependency Inversion.
*   **Practice Exercise:** Create a raw FastAPI app. Implement an endpoint `/echo` that takes JSON, validates it via Pydantic, and returns it. Build an error handler for invalid JSON.

### Weeks 5-8: Database and Architecture Surgery
*   **Study:** Relational Database Design, SQL Joins, Indexing logic.
*   **Read:** PostgreSQL documentation on Transactions and ACID compliance.
*   **Practice/Refactor Task:** Take the codebase. Implement **Phase 1 and Phase 2** of the Refactor Blueprint. Strip out the `supabase-py` Rest client. Write raw SQLAlchemy ORM queries for the `/complaints` endpoints. Prove it works.

### Weeks 9-10: Frontend and State Management Mastery
*   **Study:** React Component Lifecycle, Virtual DOM Theory, React Context API.
*   **Read:** TkDodo's blog on React Query (The definitive guide to TanStack Query).
*   **Practice/Refactor Task:** Implement **Phase 3** of the Refactor Blueprint. Strip out the manual polling. Implement `useQuery`. Verify the React devtools do not show unnecessary re-renders.

### Weeks 11-12: The Distributed System Mindset
*   **Study:** Idempotency, Queueing Theory, API Security.
*   **Build Task:** Set up Celery and Redis locally. Rip out `BackgroundTasks` from FastAPI. Move the `email_client` into a Celery worker. Force crash the worker, prove the task stays in Redis, restart the worker, and watch the email send successfully. You are now a Senior.

---

## 11. Hidden Lessons From This Codebase

Evaluate this system with brutal, objective engineering reality.

*   **Engineering Maturity Score: 4/10**
    *   *Why:* Mixing SQLAlchemy ORM model definitions with direct Supabase PostgREST client executions shows a deep misunderstanding of database interaction layers. Internal loopback HTTP requests instead of function calls show a misunderstanding of monolithic structure.
*   **Maintainability Score: 5/10**
    *   *Why:* There are no tests, and logic is trapped in routers. However, Python and FastAPI are readable, and the file structure itself is logical.
*   **Scalability Score: 2/10**
    *   *Why:* 30-second manual React polling + HTTP REST database client requests = immediate bottleneck at scale.
*   **Tech Debt Risk: HIGH**
    *   *Why:* The MVP was built to prove concept quickly, which it did. If features are added without executing the Refactoring Blueprint first, the system will collapse under its own weight in 3 months.
*   **What a Senior would immediately fix:** They would delete the `httpx.post(localhost)` from the webhook, rewrite route database logic into a dedicated Service layer, and replace `setInterval` with React Query.

---
**End of Document.**  
*Master the concepts written here, and you don't just master this project—you master backend software engineering.*

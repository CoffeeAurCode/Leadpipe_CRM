# Staff Engineer Mentorship Manual: Tenant Management MVP

Welcome to the definitive engineering guide for the Tenant Management MVP. This document is not a simple summary of the codebase. Instead, it is a staff-level reverse-engineering effort designed to rip apart the system, expose its inner workings, evaluate its architectural decisions (the good, the bad, and the ugly), and teach you how to think like a senior engineer while working on it. 

If you read and Internalize this manual, you will be able to confidently debug, extend, and scale this system.

---

## 1. Big Picture Architecture

### What kind of system is this?
This is an **Event-Driven, AI-Augmented Web Application**. It functions as a bridge between asynchronous voice interactions (via Vapi and Groq) and a synchronous dashboard (React). 

### Architectural Style
Currently, it operates as a **Modular Monolith**. 
- The backend is a single FastAPI application containing all domains (Complaints, Properties, Flats, Rents, Voice Webhook).
- The frontend is a Single Page Application (SPA) built with React and Vite.

### Why this architecture was likely chosen
For an MVP, speed of iteration is the ultimate metric. A Modular Monolith allows for rapid feature deployment without the massive DevOps overhead of microservices. Python (FastAPI) is the industry standard for AI integrations, making stringing together Groq and Vapi seamless. React with Tailwind enables rapid prototyping of a premium-feeling "Bento Grid" UI.

### Strengths & Weaknesses
*   **Strengths:** Incredibly fast to iterate on; single repository overhead; brilliant use of Python's `BackgroundTasks` to offload email notifications without blocking webhook responses.
*   **Weaknesses:** Complete lack of structural separation between data access and business logic. The system has a fatal design flaw: it declares SQLAlchemy models (`db/models.py`) but queries the database directly using the `supabase-py` PostgREST client in the route handlers.

### How Data Flows End-to-End (The Request Lifecycle)
**Scenario: A tenant calls the system to complain about a leaking pipe.**
1.  **Frontend/Entry:** Tenant dials the Vapi-hosted phone number. 
2.  **Voice Interaction:** Vapi converses with the user. Once the user confirms the complaint via the `submit_complaint` tool, Vapi triggers a `POST` to the backend's `/voice/webhook`.
3.  **Webhook Ingestion (`routes/voice.py`):** The backend receives the JSON payload. It parses the final event report (`tool-calls` or `end-of-call-report`).
4.  **AI Extraction (`ai/extractor.py`):** The system takes the unformatted transcript and pushes it to Groq (Llama 3.1) to cleanly extract `{flat_number, category, priority, description}`.
5.  **Idempotency Check:** The backend checks the `call_logs` table using the `call_id` to ensure it hasn't processed this exact voice call already.
6.  **Loopback Anti-Pattern:** Instead of calling a service function, the webhook handler uses `httpx.AsyncClient` to make an HTTP POST request *back to its own server's `/complaints` endpoint*. 
7.  **Database Write (`routes/complaints.py`):** The `/complaints` endpoint receives the POST. It uses `db.table("complaints").insert()` (Supabase PostgREST client) to write to Postgres. 
8.  **Asynchronous Notification:** A FastApi `BackgroundTask` is spawned to trigger SendGrid (`email_client.py`) to notify the manager.
9.  **Frontend Render:** The React dashboard, which is aggressively polling the `/complaints` endpoint every 30 seconds (`App.jsx`), hits the backend, receives the newly created complaint, and updates the Bento Grid UI.

---

## 2. Backend Deep Dive

### A. Entry Layer (Routes / Controllers)
*   **Pattern used:** Standard FastAPI router pattern. Endpoints like `/complaints`, `/properties`, and `/voice` are separated into modules.
*   **Validation:** Excellent use of Pydantic (`app.schemas`) for strict request/response validation.
*   **Response modeling:** Returns raw dictionaries from the Supabase client directly to the client.
*   **Error Handling Philosophy:** Highly defensive in the webhook (`Always return 200 to prevent retry loops`), but overly generic (`HTTPException 500` for all unexpected errors) elsewhere.
*   **Anti-pattern - The Loopback Hack:** Inside `routes/voice.py`, after extracting AI data, the system spawns an asynchronous HTTP request to `localhost:8000/complaints` to save the data. **This is highly dangerous.** In a production environment with multiple workers (e.g., Gunicorn/Uvicorn), this wastes thread pools and can cause network timeouts just to talk to itself. 

### B. Business Logic Layer
*   **Separation of Concerns:** Non-existent. Business rules live directly inside the FastAPI route definitions. 
*   **Coupling Issues:** The logic to map a `flat_number` to a `flat_uuid` and then assign a `tenant_uuid` is baked heavily into `routes/complaints.py`. If you ever need to create a complaint from a CRON job or an internal script, you have to duplicate this exact logic.
*   **Refactoring to Senior-Grade:** Moving forward, routes should ONLY handle HTTP parsing. They should pass data to a `ComplaintService.create_complaint()` class/function, which then handles the database writes. 

### C. Database Layer
*   **ORM Usage (The Split-Brain Problem):** The project defines SQLAlchemy models (`models.py`) and uses Alembic for migrations, making you think it's an ORM-based app. But if you look at the routes (e.g., `db.table("complaints").select()`), it actually uses the Supabase Python Client (a wrapper around PostgREST APIs). This means you have zero type safety on your queries, and your SQLAlchemy models are ONLY serving as a schema definition for Alembic.
*   **Performance Risks:** Using Supabase PostgREST over the network for every operation creates massive HTTP overhead compared to a direct TCP connection via `psycopg2`/`asyncpg`. 
*   **Transaction Handling:** Because it uses the Supabase HTTP client, there are **no atomic transactions**. If creating a complaint succeeds but creating the linked appointment fails, you are left with orphaned data.

### D. Integrations
*   **Vapi Webhook:** Exceptionally well done structurally. The implementation understands that Vapi sends noisy status events and correctly filters for `tool-calls` or `end-of-call-report` first.
*   **Idempotency:** The webhook is properly protected. It checks the `call_logs` table using the unique `call_id` before inserting a complaint. If Vapi retries the webhook due to a network glitch, the system safely ignores it.
*   **Failure Management:** In SendGrid (`email_client.py`), failures are caught and logged, which is correct since notifications shouldn't crash the main thread. However, there is no retry queue. If SendGrid goes down, the email is lost forever.

---

## 3. Frontend Deep Dive

### State Management & Data Fetching
*   **Architecture:** Entirely localized React state (`useState`) passed down via severe prop-drilling into the Bento Grid components. 
*   **Data Fetching:** Standard `fetch()` wrapped in an `useEffect()` on component mount, coupled with a pure JavaScript `setInterval()` polling the backend every 30 seconds for new complaints.
*   **Re-render Risks:** Every 30 seconds, `loadComplaints()` runs. It resets the `complaints` array state, which triggers a complete re-render of the entire `BentoDashboard` and its children. If the manager is mid-scroll or analyzing a ticket, the UI might violently flash or reset.

### Component Structure
*   **Separation of UI vs Logic:** Fairly decent. `App.jsx` handles the heavy lifting of state, and dumb components like `CompactComplaintCard` simply render what they are given.
*   **How a senior would structure it differently:** A senior engineer would immediately rip out the `setInterval()` polling. It does not scale. They would implement React Query (TanStack Query) for sophisticated caching, deduplication, and background refetching, or use WebSockets/Server-Sent Events (SSE) from FastAPI to push instant updates.

---

## 4. Cross-Cutting Concerns

### Security & Observability 
*   **Authentication:** Currently non-existent. CORS is wide open (`allow_origins=["*"]`). Anyone who knows the URL can modify manager complaints. 
*   **Logging:** Relying on `print()` for the core webhook debugging. In a concurrent system, these lines will intertwine and become unreadable. Python's built-in `logging` (or better, `structlog` for JSON logs) is mandatory.

### Scalability Under Load
*   **100 Users:** Works perfectly. Polling is harmless. The system feels snappy.
*   **10,000 Users:** The backend dies. 10,000 browsers hitting `/complaints` every 30 seconds generates ~330 requests per second (RPS). Supabase's PostgREST API will start rate-limiting the backend, and the FastAPI application will exhaust its connection pool.
*   **1,000,000 Users:** Impossible without severe architectural redesign (Redis caching, WebSockets instead of polling, direct PostgreSQL TCP connections instead of HTTP-based Supabase queries).

---

## 5. Hidden Engineering Lessons

*   **Premature Abstraction:** The AI rule-based fallback inside `extractor.py` (`extract_fields` via Regex). While clever, Llama 3.1 via Groq is fast and reliable enough that maintaining complex Regex for alphanumeric edge cases provides diminishing returns relative to the maintenance burden.
*   **Missing Abstraction:** **The Service Layer.** By putting database queries inside route handlers, everything is tightly coupled. If you want to change from Supabase to a raw AWS RDS PostgreSQL instance, you literally have to rewrite every single route file in the codebase.
*   **The "Double Network" Trap:** `voice.py` does HTTP -> `main.py` -> HTTP -> Supabase. You are relying on two separate network hops to save one piece of data. This introduces massive latency. 

---

## 6. Senior-Level Refactor Roadmap

If I took over this codebase tomorrow, here is exactly how I would prioritize the refactor:

### Phase 1: Make it Stable (The "Stop the Bleeding" Phase)
*   **Action:** Remove the loopback HTTP call in `voice.py`.
*   **Why:** It is a critical failure point. Webhooks need to be fast. 
*   **Code Pattern (Before):** `await httpx.AsyncClient().post("localhost:8000/complaints")`
*   **Code Pattern (After):** `await ComplaintService.create_from_voice(complaint_payload)`

### Phase 2: Make it Clean (The "Service Layer" Phase)
*   **Action:** Commit to either SQLAlchemy OR Supabase PostgREST, and move them into a `services/` folder. Do not use both. 
*   **Why:** Currently, testing logic is impossible without a live database. A service layer allows unit testing business logic in isolation.

### Phase 3: Make it Scalable (The Frontend Evolution)
*   **Action:** Deprecate 30-second `setInterval()`. Install TanStack React Query.
*   **Why:** React Query provides built-in `stale-while-revalidate` fetching. It caches the data, meaning zero UI flashing for the manager, and reduces unnecessary backend hammering if the data hasn't changed.

### Phase 4: Make it Production-Grade
*   **Action:** Implement JWT Authentication via Supabase Auth. Set up Datadog or Sentry for production exception monitoring. Restrict CORS. Use WebSockets.

---

## 7. Debugging Mastery Guide

### Tracing a Webhook Bug (The Ghost Call)
"A tenant says they called, but the complaint is missing from the dashboard."
1.  **Start at the Edge:** Check Vapi's log dashboard. Did Vapi actually hit your webhook? What was the HTTP response?
2.  **Check Idempotency Guard:** Query `select * from call_logs order by created_at desc limit 10;`. Do you see the `call_id`? If `complaint_status` says `incomplete`, it means Groq's AI failed to extract mandatory fields. The user hung up too early.
3.  **Check Internal Loopback:** If it says `failed`, the `httpx.post` inside `voice.py` failed. Check FastAPI logs for a 500 error originating from `/complaints`.

### Reasoning about Async Race Conditions
In FastAPI, `def` runs in a synchronous threadpool, `async def` runs in the main async event loop. 
If SendGrid was synchronous but placed in an `async def` route without `BackgroundTasks`, it would freeze the entire server while waiting for the HTTP handshake, causing Vapi webhooks to timeout and retry, which would create a cascading failure loop. Always use `background_tasks.add_task` for external notifications.

---

## 8. Mental Models Required to Master This Codebase

1.  **Event-Driven Systems & Idempotency:** Understand that in the real world, webhooks will trigger multiple times. Your system must be designed mathematically so that `f(x) = f(f(x))`. This codebase achieves it via unique `call_log.call_id` constraints. 
2.  **The HTTP Lifecycle:** You must conceptualize the exact timeline of a request, from DNS resolution to the backend, through the FastAPI `CORSMiddleware`, routed to the function, executing the DB call, and returning the JSON.
3.  **Clean Architecture (Separation of Concerns):** The mental model of decoupling "How data is accessed" (Database), "What the data does" (Business Logic), and "How data is presented" (API/React).
4.  **Optimistic UI Updates:** For React, understanding how to update local state *before* the server responds to make the app feel instant, then rolling back if the API fails.

**Curated Reading List for Interns:**
*   *Architecture Patterns with Python* (Cosmic Python) by Harry Percival. (Critical for fixing the Database/Service layer anti-patterns here).
*   *Designing Data-Intensive Applications* by Martin Kleppmann (For understanding Database transactions and scalability limits).
*   *TanStack Query Documentation* (For frontend data fetching mastery).

---

## 9. If an Intern Had to Rebuild This From Scratch (Structured Roadmap)

**Week 1–2: Foundations & APIs**
*   **Skill:** Build a raw FastAPI server from scratch. Implement Pydantic models. Understand HTTP verbs, status codes, and JSON serialization. 
*   **Build:** A simple in-memory CRUD app for "Complaints". 

**Week 3–4: Database Mastery**
*   **Skill:** Raw SQL first, then SQLAlchemy ORM. Understand Foreign Keys, Cascade deletes, and DB Normalization.
*   **Build:** Wire the Week 2 app to PostgreSQL. Implement the `flats -> tenants -> complaints` hierarchy.

**Week 5–6: Clean Architecture & Backend**
*   **Skill:** Refactoring. Moving code out of routes and into Service Classes and Repositories.
*   **Build:** Refactor the Week 4 app to have zero `db.session` calls inside the FastAPI routes.

**Week 7–8: Frontend Foundations**
*   **Skill:** React mental models. State vs Props, `useEffect` lifecycles, and Tailwind styling.
*   **Build:** The basic UI. Hardcode the dummy data to get the Bento grid looking visually perfect without an API.

**Week 9–10: The Intersection (Integrations)**
*   **Skill:** Webhook theory, Idempotency, and Prompt Engineering.
*   **Build:** Connect the React frontend to the backend using `fetch()`. Implement the Vapi webhook endpoint and integrate Groq LLM.

**Week 11–12: Scaling & Production Hardening**
*   **Skill:** Real-time optimization and Security.
*   **Build:** Rip out the 30-second polling. Implement FastAPI WebSockets for real-time dashboard updates. Ensure CORS and Auth are locked down.

---

## 10. Brutally Honest Evaluation

Evaluate this codebase like a Staff Engineer doing a technical due-diligence audit.

*   **Engineering Maturity Level (4/10):** The app demonstrates good high-level concepts (Idempotency, AI pipelines, React grid logic) but fails on fundamental software engineering principles. The mixture of raw Supabase HTTP clients operating alongside SQLAlchemy models indicates a deep architectural confusion. It is a script pretending to be an application.
*   **Production Readiness (3/10):** It lacks authentication, robust error logging, and standard system metrics. Open CORS and loopback internal HTTP requests are showstoppers for production deployment. The app will work fine for an internal test of 10 people, but cannot be sold to an enterprise.
*   **Maintainability (5/10):** Moderate. Because it's a monolithic FastAPI app, it's easy to trace execution from top to bottom. However, because business logic and data access are intertwined in the routes, writing automated unit tests is practically impossible without mocking the entire internet.
*   **Scalability (3/10):** Very poor. Frontend polling every 30 seconds combined with Supabase REST API calls in the backend means this application will DDoS its own database before it even reaches a moderate user base. 

**Summary:** This is a fantastic MVP. It is exactly what an MVP should be—scrappy, fast, and feature-complete to prove the business value. However, it must undergo a severe "Phase 1 & 2" refactor before the engineering team adds a single new feature.

---

# PART 2: THE DEEP DIAGNOSTICS & MISSING MANUAL

## 11. Technology Stack Deep Breakdown 

To master this project, you cannot just know the syntax. You must understand how the tools operate inside the interpreter and across the network.

### 1. FastAPI (The Core Framework)
*   **What it is:** A modern, fast web framework for building APIs with Python, based on standard Python type hints.
*   **Why it is used here:** Standard Python synchronous web frameworks (like Django or Flask without extensions) block the main thread while waiting for network I/O. Because this app integrates heavily with external APIs (Vapi, Groq, SendGrid), async I/O is critical to prevent a single voice call from freezing the whole server.
*   **How it works internally:** It is a wrapper around two major libraries: **Starlette** (for the ASGI event loop and routing) and **Pydantic** (for data validation).
*   **How this project uses it:** Endpoints grouped by APIRouters (`routes/voice.py`, `routes/complaints.py`). Uses `BackgroundTasks` heavily to offload non-critical side effects (like SendGrid emails).
*   **Common beginner misunderstandings:** The difference between `def` and `async def`. If you define a route `async def my_route()` but place a synchronous blocking call inside it (e.g., `time.sleep(5)` or `requests.get()`), you will freeze the *entire event loop*. If you define it as `def my_route()`, FastAPI smartly shunts it to an external threadpool. This codebase mixes synchronous Supabase client calls inside `async def` routes, which is a major concurrency risk.
*   **Advanced internals:** ASGI (Asynchronous Server Gateway Interface) vs WSGI. Understand how Uvicorn manages the event loop.

### 2. Vapi & Groq (The Voice/AI Brain)
*   **What it is:** Vapi handles raw telephony, Speech-to-Text (STT), Text-to-Speech (TTS), and latency management. Groq hosts LLMs (Llama 3.1) running on specialized LPUs (Language Processing Units) rather than GPUs, providing extreme token generation speed.
*   **Why it is used here:** Groq's sub-second latency is required so the AI sounds human during voice calls. Vapi removes the burden of handling SIP trunks, WebRTC, and buffering.
*   **How it works internally:** Vapi streams audio websocket chunks. When the caller pauses, Vapi invokes the LLM, reads the stream back, and plays TTS. Critically, we give Vapi a "Tool" called `submit_complaint`. When the LLM decides the user has provided enough info, it outputs a JSON tool call, which Vapi translates into an HTTP POST request to our `/voice/webhook`.

### 3. Pydantic (Clean Data Boundaries)
*   **What it is:** Data validation and settings management using Python type hints.
*   **How this project uses it:** Found in `app/schemas/`. Everything entering the API `WebhookPayload` or `ComplaintCreate` is verified here.
*   **Common beginner misunderstandings:** Pydantic models are *not* database models. They are data transfer objects (DTOs). If a payload fails validation, Pydantic immediately throws an `HTTP 422 Unprocessable Entity` error before your route logic ever executes.

### 4. Supabase Python Client vs SQLAlchemy (The Identity Crisis)
*   **What it is:** Supabase is a managed PostgreSQL host that wraps the database in a PostgREST API. SQLAlchemy is a Python ORM that executes raw SQL over TCP.
*   **How this project uses it:** The project uses SQLAlchemy models (`models.py`) and Alembic to create the tables natively. But to *read and write* data, it uses `supabase.table("complaints").insert()`. 
*   **Advanced internals & Risks:** `supabase-py` makes an HTTP request. This means no persistent connection pool, massive overhead per query, and absolute loss of transaction control. **This is the system's biggest flaw.** You cannot wrap a Supabase PostgREST insert and a second insert into a SQL `BEGIN ... COMMIT` block. If one fails, data integrity is compromised.

---

## 12. Complete Visual Architecture Maps

*These diagrams show what actually happens in the code, exposing both the intentional designs and the accidental complexity.*

### A. Core Request Lifecycle (Sequence Diagram)
**Scenario: Voice Webhook triggers a Complaint Creation**

```text
[Caller] --(Voice)--> [Vapi] 
                        |
                        |-- (Webhook POST tool-calls) --> [FastAPI: routes/voice.py]
                                                              |
    [Groq / Llama 3] <--(Extracts struct data)-- (ai/extractor.py)
                                                              |
                  <--(Idempotency Check)-- [PostgreSQL: call_logs]
                                                              |
                                        [WARNING: LOOPBACK ANTI-PATTERN]
                  --(httpx.post local)--> [FastAPI: routes/complaints.py]
                                                    |
                                                    |-- (Supabase HTTP insert) --> [PostgreSQL: complains]
                                                    |
                                                    |-- (BackgroundTasks) --> [SendGrid email_client.py]
                                                    |
                  <--(HTTP 200 OK)------------------+
                        |
[Vapi] <--(200 OK)------+
  |
(TTS: "Your complaint was recorded")
```

### B. Database ER Diagram (ASCII)

```text
+----------------+       +-------------------+       +-----------------+
|   Properties   |       |    Buildings      |       |      Units      |
+----------------+       +-------------------+       +-----------------+
| id (UUID)      |<------| property_id       |<------| property_id     |
| name           |       | id (UUID)         |       | building_id     |
| address        |       | name              |<------| id (UUID)       |
+----------------+       +-------------------+       | unit_number     |
                                                     +-----------------+
                                                              ^
                                                              |
+----------------+       +-------------------+                |
| Appointments   |       |   Complaints      |                |
+----------------+       +-------------------+                |
| id (UUID)      |-1:1---| complaint_id      |                |
| appointment_date|      | unit_id           |----------------+
| manager_id     |       | tenant_id         |-------------------------+
+----------------+       | category          |                         |
                         | priority          |                         |
                         | status            |                         |
                         +-------------------+                         |
                                                                       |
+----------------+       +-------------------+                         |
|   Call Logs    |       |     Tenants       |                         |
+----------------+       +-------------------+                         |
| id (UUID)      |       | id (UUID)         |<------------------------+
| call_id        |       | phone_number      |
| event_type     |       | unit_id           |
| transcript     |       | name              |
+----------------+       +-------------------+
```

---

## 13. Debugging & Failure Playbook

### Scenario A: 500 Errors on `/buildings` or `/complaints`
*   **The Problem:** Manager clicks "Add Building," frontend spins, network tab shows `500 Internal Server Error`.
*   **Step-by-Step Debugging:**
    1.  **Check Terminal output.** You will likely see `httpx.HTTPStatusError: 400 Bad Request`.
    2.  **Why it happened:** The Supabase HTTP client throws random HTTP 400s if a foreign key constraint fails (e.g., the `property_id` passed doesn't exist in the properties table). 
    3.  **The Fix:** Wrap the Supabase call in a `try...except APIError`. Because the codebase lacks a global exception handler for PostgREST errors, these bubble up as unhandled 500s.

### Scenario B: The Webhook "Ghost Call" Race Condition
*   **The Problem:** Vapi logs say a webhook was sent, and it received a `200 OK`. Yet, no complaint exists in the database.
*   **Step-by-Step Debugging:**
    1.  Look at `routes/voice.py`. It uses a background task or an internal `httpx` loopback to create the complaint.
    2.  If the loopback fails (e.g., validation error on `category`), the `routes/complaints.py` returns a 422 or 500. 
    3.  Because `voice.py` ignores the response of its own loopback call (`await client.post(...)` without checking `response.raise_for_status()`), the error is swallowed silently. `voice.py` returns `200 OK` to Vapi, but the complaint was rejected.
    4.  **The Fix:** Eradicate the loopback. Call `await create_complaint_logic()` directly so exceptions propagate and can be logged properly.

### Scenario C: UI Stale State (The Phantom Update)
*   **The Problem:** A manager updates a complaint to "resolved", but 30 seconds later, it flashes back to "pending".
*   **Why it happened:** The `setInterval` polling in `App.jsx` fetched the complaint list *while* the manager's `POST /update` request was still in flight. The poll receives the old data. When the poll finishes, it resets the React state to the old data.
*   **The Fix:** On mutation (updating status), use optimistic UI updates. Better yet, refactor the polling out and use React Query.

---

## 14. Testing Mastery

To prove you are a staff-level operator in this codebase, you must implement tests that don't just mock everything, but verify the boundaries of the system.

### A. The Unit Testing Strategy
*   **Goal:** Test `ai/extractor.py` without hitting the Groq API (saves money, runs instantly).
*   **How:** Use `unittest.mock.patch` to mock the Groq client.
*   **Code Example:**
```python
from unittest.mock import patch
from app.ai.extractor import extract_fields

@patch("app.ai.extractor.client.chat.completions.create")
def test_extract_fields_parses_JSON_correctly(mock_groq):
    mock_groq.return_value.choices[0].message.content = '{"flat_number": "101", "category": "plumbing"}'
    transcript = "My pipe is leaking in flat 101."
    result = extract_fields(transcript)
    assert result["category"] == "plumbing"
    assert result["flat_number"] == "101"
```

### B. The Integration Testing Strategy (The "Webhook Simulator")
*   **Goal:** Prove that if Vapi sends a valid payload, the database actually gets a complaint and an email task is queued.
*   **How:** Use FastAPI's `TestClient` and an ephemeral PostgreSQL database container (Testcontainers).
*   **What to test:** 
    1. Send a payload to `/voice/webhook`.
    2. Query the actual DB to ensure the `call_logs` idempotency row was written.
    3. Query the DB to ensure `complaints` was written.
    4. Assert the `BackgroundTasks` received the email job.

---

## 15. Real-World Production Engineering

If you are tasked with scaling this MVP, here is how you must think.

### Stage 1: Scaling to 100 Users (The immediate future)
*   **Risk:** SendGrid API rate limits or network timeouts will eventually crash requests.
*   **Action Required:** Keep the current architecture but wrap all external calls (Supabase, SendGrid, Groq) in `tenacity` retry loops. Implement a global `structlog` logger tracking `call_id` across the entire request context using `contextvars`.

### Stage 2: Scaling to 10,000 Users (The architectural breaking point)
*   **Risk:** The 30-second frontend polling interval. 10,000 users = 330 requests per second. Supabase's HTTP proxy will die. FastAPI's worker thread pool will exhaust.
*   **Action Required:**
    1.  **Stop Polling:** Implement FastAPI WebSockets or Server-Sent Events (SSE). Only push state to the client when a DB mutation occurs.
    2.  **Rip out Supabase HTTP:** Switch `db.py` to use `asyncpg` combined with SQLAlchemy 2.0. Open a persistent TCP connection pool using `PgBouncer`.
    3.  **Background Queueing:** Move SendGrid emails and heavy AI extractions out of `BackgroundTasks` (which map 1:1 to memory) and into a robust message broker like **Celery** or **ARQ** backed by Redis.

### Stage 3: Scaling to 1,000,000 Users
*   **Risk:** Monolithic database contention. Webhook endpoints getting starved by long-running queries serving the dashboard.
*   **Action Required:** Read/Write replica splitting (CQRS). Move the Vapi ingestion into its own isolated microservice cluster (Node.js/Go or a tuned FastAPI app) that solely writes to an event stream (Kafka). The core API reads from Kafka and updates the database asynchronously.

---

## 16. Technical Concept Primers (Linked to Codebase)

A senior engineer doesn't memorize syntax; they master foundational concepts.

### 1. HTTP Lifecycle & Webhooks
A webhook is just a reverse API. Instead of us asking Vapi "Did the user say anything?", Vapi POSTs to us when they do. Understanding this means understanding that *we* must quickly return an HTTP `200 OK` so Vapi doesn't think we died. Doing synchronous, heavy AI computation *before* returning `200 OK` is dangerous.

### 2. Idempotency 
*   **Concept:** Repeating an action multiple times yields the same result as doing it once.
*   **In this codebase:** Vapi has strict timeout limits. If our webhook takes too long, Vapi will assume it failed and resend the *exact same webhook payload*. If we don't handle this, we will create duplicate complaints and send duplicate emails. Checking `call_logs` by `call_id` before inserting a complaint is our idempotency guard.

### 3. Separation of Concerns & Clean Architecture
*   **Concept:** Code that touches the internet (Routers) should not know how data is saved (Database).
*   **In this codebase:** FastApi routes (`def create_complaint(...)`) manually construct Supabase insert statements. If we change databases, the API breaks. A senior engineer creates a `ComplaintRepository` interface. The Route calls the Repository. The Repository talks to the Database.

### 4. Transactions and ACID Data Integrity
*   **A = Atomicity:** A transaction is "all or nothing."
*   **In this codebase:** When we create a complaint, and then optionally create an appointment based on AI data... what if the appointment insertion fails? The complaint is already saved, but the appointment is missing. Because we use HTTP REST `supabase.insert()`, we have no SQL `ROLLBACK` capability. This is a crucial architecture defect you must eventually fix by using a proper Python DB driver (`asyncpg` or `psycopg3`).

---

**FINAL MANDATE FOR THE READER:**
Do not simply read this and move on. Identify one of the flaws outlined above—like the internal HTTP loopback in `routes/voice.py`—and fix it today. Write a unit test for it. Observe how the system's stability increases. This is how you transition from an intern to a staff engineer.

---

# PART 3: ACCUMULATED WISDOM FROM 22 SESSIONS OF REAL PRODUCTION DEBUGGING

> This section was written after 22 complete development sessions on this codebase. Every lesson here came from a real bug, a real production issue, or a real architectural decision that had to be made under pressure. Reading Parts 1 and 2 teaches you the theory. This part teaches you what actually happens.

---

## 17. Updated Architecture Assessment — Current State

Parts 1 and 2 were written early in the project. The system has evolved significantly. Here is the honest current state:

| Concern | Early State (Parts 1–2) | Current State |
|---------|------------------------|---------------|
| Authentication | None — CORS wide open | Supabase Auth + JWT validation + Subscription gate |
| RLS | Not deployed | Fully deployed on all user-facing tables |
| Voice webhook DB client | Anon key (wrong) | Service role key (correct — fixed after testing revealed VAPI has no JWT) |
| Internal loopback in `voice.py` | Still present | Removed — complaint creation now calls service functions directly |
| Frontend polling | 30s setInterval | Still present — acceptable at current scale |
| SQLAlchemy/Supabase split brain | Present | SQLAlchemy models kept only as schema reference; all queries use Supabase SDK |
| Production auth | Absent | Google OAuth PKCE flow across two domains |
| Payment gate | Absent | Stripe subscription gate on all routes |

**Revised maturity assessment:**
- Engineering Maturity: 6/10 (up from 4/10 — auth, RLS, and subscription gate are production-grade)
- Production Readiness: 6/10 (up from 3/10 — auth works, RLS works, but still no structured logging, no retry queues)
- Maintainability: 6/10 (still no service layer, but patterns are now consistent)
- Scalability: 3/10 (unchanged — polling + Supabase HTTP are still the ceiling)

---

## 18. The Four Categories of Bugs You Will Encounter

After 22 sessions, every bug falls into one of four categories. Knowing the category immediately tells you where to look.

### Category 1 — Infrastructure Bugs (Hardest to Anticipate)

**Pattern:** Code logic is correct; the *environment assumption* is wrong.

**Canonical example:** VAPI endpoints using `get_db` (anon client) instead of `get_service_db`.

The code was logically sound. VAPI returns the right shape. But VAPI makes machine-to-machine calls with no user JWT. The anon Supabase client with RLS active returns 0 rows for every query because `auth.uid()` is null. The endpoint looks correct in isolation — it only breaks in the live VAPI environment.

**The diagnostic question:** "Who calls this endpoint, and do they have a user JWT?"

| Caller | Has JWT? | Required client |
|--------|----------|----------------|
| Logged-in manager (browser) | Yes | `get_authenticated_db` |
| VAPI webhook or tool call | No | `get_service_db` |
| Stripe webhook | No | `get_service_db` |
| Twilio callback | No | `get_service_db` |
| FastAPI BackgroundTask | No | `get_service_db` (pass client explicitly as an arg) |

**Rule:** Write this question in every webhook/tool endpoint before you write the first line of business logic: *"Does the caller of this endpoint have a JWT?"*

---

### Category 2 — Platform-Specific Bugs (Windows vs Linux)

**Pattern:** Works on macOS/Linux, crashes on Windows.

**Canonical example:** `print(f" ✓ User confirmed")` in a FastAPI route crashed the Windows development server with `UnicodeEncodeError: 'charmap' codec can't encode character`.

Windows terminal encoding defaults to `cp1252`. macOS and Linux default to UTF-8. A Unicode check mark `✓` is valid UTF-8 but not valid `cp1252`. The bug is invisible until someone runs the code on Windows.

**Rule:** All server-side `print()` and log statements must use ASCII-only characters. Replace `✓` → `[OK]`, `✗` → `[FAIL]`, emoji → nothing.

**Secondary rule:** When a bug appears on Windows but not Linux (or vice versa), immediately search all `print()` statements for non-ASCII characters. This is almost always the cause.

---

### Category 3 — Logic Bugs in Query Scoping

**Pattern:** A query returns data from the wrong tenant/manager/group because a filter was not re-applied in a fallback branch.

**Canonical example:** `find_listing` had a two-phase query (find by flat number, then fall back to title match). The primary query had `.eq("property_group_id", pg_id)`. The fallback branch did not. A caller on Group A's dedicated phone line could return listings from Group B.

```python
# PRIMARY — correct
results = q.ilike("flat_number", f"%{query}%").eq("property_group_id", pg_id).execute()

# FALLBACK — Bug: missing .eq("property_group_id", pg_id)
fallback = db.table("lease_listings").select(...).ilike("title", f"%{query}%").execute()
# ↑ Returns ALL managers' listings that match the title — data isolation failure
```

**The diagnostic question to ask after writing every query branch:** "If I were a different manager right now, would this query return MY data or someone else's?"

**Rule:** Every branch that queries user-owned data — primary, fallback, or exception — must apply the same scope filters. Copy-paste the filters into every branch; don't assume they "carry over."

---

### Category 4 — Data Type Bugs

**Pattern:** Pydantic validates successfully, but the database SDK rejects the value because Python's type doesn't serialize to what the SDK expects.

**Canonical example:** Pydantic's `Decimal` type (used for `monthly_rent: Decimal`) doesn't serialize to JSON automatically. After `body.model_dump()`, the dict contains `Decimal("25000")`. The Supabase Python SDK throws `TypeError: Object of type Decimal is not JSON serializable`.

**The fix pattern — apply immediately after every `model_dump()`:**
```python
from decimal import Decimal

payload = body.model_dump(exclude_none=True)
payload = {k: float(v) if isinstance(v, Decimal) else v for k, v in payload.items()}
svc_db.table("lease_listings").insert(payload).execute()
```

**Why Decimal at all?** `float(1.5)` can be `1.4999999999999998` in IEEE 754 binary. `Decimal("1.5")` is exactly 1.5. Pydantic uses Decimal for financial fields to prevent rounding errors during Python-level validation. Convert to float only at the DB boundary.

---

## 19. The Three-Layer Status Rule

This is the single most important rule for preventing silent production breakage. Any time you add a new status value (for appointments, complaints, leads, subscriptions, or any other entity), you must update **all three layers** in the same commit:

```
Layer 1: PostgreSQL CHECK constraint  (the database — the last line of defense)
Layer 2: Pydantic Enum or validator   (the API — the first line of defense)
Layer 3: Frontend constants / config  (the UI — what users see)
```

**How each layer fails independently:**

| Missing layer | Symptom | When it breaks |
|---------------|---------|----------------|
| Layer 1 (DB constraint) | HTTP 500 on write — "constraint violation" | On any write to the DB |
| Layer 2 (Pydantic) | HTTP 422 — "Input should be one of..." | On the API call |
| Layer 3 (Frontend) | Grey fallback styling, wrong label | On render |

The deceptive failure is **missing Layer 1 with correct Layer 2**: Pydantic accepts `"attended"` as valid, the data goes all the way to PostgreSQL, and then the DB rejects it. The error surface (HTTP 500) is far from the root cause (missing CHECK constraint value).

**How to find the current DB constraint:**
```sql
-- Run in Supabase SQL Editor
SELECT conname, consrc
FROM pg_constraint
WHERE conrelname = 'appointments'
  AND contype = 'c';
```

**How to fix it:**
```sql
-- Cannot just ALTER the constraint — must DROP and recreate
ALTER TABLE appointments
    DROP CONSTRAINT IF EXISTS appointments_status_check;

ALTER TABLE appointments
    ADD CONSTRAINT appointments_status_check
    CHECK (status IN ('scheduled', 'completed', 'cancelled', 'rescheduled', 'attended'));
```

Always save migrations as numbered SQL files in `backend/migrations/`. Never run schema changes directly without saving them.

---

## 20. The "All Code Paths" Mental Model

This is the biggest gap between junior and senior developers. Juniors implement the happy path. Seniors find and implement all paths.

**Example — appointment cancellation has four independent entry points:**
```
1. Calendar UI      → PATCH /appointments/{id}
2. VAPI voice call  → POST /appointments/cancel
3. AI chatbot tool  → execute_tool("cancel_appointment")
4. Future path?     → (some admin endpoint, import script, etc.)
```

A notification that fires on 3 out of 4 paths is wrong. The tenant who happened to call the voice agent instead of using the UI gets no notification.

**The audit process — before shipping any feature that fires side effects:**
1. Draw every entry point that triggers the action
2. For each entry point, trace the code path and check: does it call the side effect?
3. For each entry point, check: does the DB query fetch the fields the side effect needs?

**Concretely:** When adding SMS to `cancel_appointment` in the chatbot, the existing DB query fetched `"id, status, flat_number"`. The SMS function needs `flat_uuid` to look up the tenant. The code was added correctly, but silently failed because `flat_uuid` was not in `select()`. No error — just no SMS.

**Rule:** Before writing any side-effect call (notification, analytics event, audit log), list every field that call needs. Then grep the DB query in that code path and verify each field is in `select()`.

---

## 21. Reading Library Source Code — The Ground Truth

When a third-party library prop or function silently does nothing, the documentation is unreliable. The compiled dist is not.

**The situation that exposed this:** `react-joyride` v3 renamed the event callback from `callback={fn}` to `onEvent={fn}`. Every blog post, every AI assistant, every Stack Overflow answer described v2. The tour overlay appeared and worked visually but the callback was never called — tours frozen at step 1.

**The diagnostic process:**
```bash
# 1. Check what version is actually installed (^ in package.json means "at least this version")
cat frontend/node_modules/react-joyride/package.json | grep '"version"'

# 2. Search the compiled dist for the prop you're using
grep -n "callback" frontend/node_modules/react-joyride/dist/index.cjs | head -5
# → zero results = prop does not exist in this version

# 3. Find the correct prop name
grep -n "onEvent" frontend/node_modules/react-joyride/dist/index.cjs | head -5
# → results found = this is the real prop name
```

**The rule:** When a prop silently does nothing, there are exactly three causes:
1. The prop name changed (most common — check version, grep dist)
2. The prop is conditional on another prop being set
3. A JavaScript error earlier in the render cycle swallowed the prop

Grep the dist before trying anything else. It takes 30 seconds and immediately rules out cause #1.

---

## 22. The FastAPI Route Ordering Trap

FastAPI matches routes top-to-bottom. Literal segments must come before dynamic segments. Violating this creates an unreachable route — no error, the wrong handler runs silently.

```python
# ❌ WRONG ORDER — /rents/summary matches /{flat_uuid} first, flat_uuid="summary"
@router.get("/{flat_uuid}")
async def get_active_rent(flat_uuid: str, ...): ...

@router.get("/summary")  # UNREACHABLE — never matched
async def get_rent_summary(...): ...
```

```python
# ✅ CORRECT ORDER — literal before dynamic
@router.get("/summary")   # matched first when path is /rents/summary
async def get_rent_summary(...): ...

@router.get("/{flat_uuid}")  # matched for anything else
async def get_active_rent(flat_uuid: str, ...): ...
```

**When to apply:** Any time you add a new non-parameterized route to a router that already has `/{id}` or `/{uuid}` routes.

**Common traps in this codebase:** `/rents/summary` must be before `/rents/{flat_uuid}`. `/call-logs/stats` must be before the generic `GET /call-logs`.

**The verification command:**
```bash
curl -s http://localhost:8000/openapi.json | python -c "
import json, sys
spec = json.load(sys.stdin)
for path in sorted(spec['paths'].keys()):
    print(path)
"
```
If you see `summary` not in the list or see it grouped under a parameterized path, the ordering is wrong.

---

## 23. The Bidirectional FK Update Pattern

This codebase has a bidirectional pointer between `flats` and `tenants`:
- `flats.tenant_uuid` → points to who lives there
- `tenants.flat_uuid` → points to where the tenant lives

When assigning or unassigning, both must be updated atomically (or as close to it as possible without real transactions). Updating only one creates an inconsistent state where one record says "flat A101 has tenant X" but the tenant record says "I live in no flat."

**Assign (update both — order doesn't matter):**
```python
db.table("flats").update({
    "tenant_uuid": body.tenant_uuid,
    "occupied": True,
}).eq("uuid", flat_uuid).execute()

db.table("tenants").update({
    "flat_uuid": flat_uuid,
}).eq("uuid", body.tenant_uuid).execute()
```

**Unassign (order matters — read first, then clear both):**
```python
# 1. Read first — you need tenant_uuid before you clear it
flat = db.table("flats").select("tenant_uuid").eq("uuid", flat_uuid).execute()
tenant_uuid = flat.data[0].get("tenant_uuid") if flat.data else None

# 2. Clear tenant's flat reference
if tenant_uuid:
    db.table("tenants").update({"flat_uuid": None}).eq("uuid", tenant_uuid).execute()

# 3. Clear flat's tenant reference
db.table("flats").update({"tenant_uuid": None, "occupied": False}).eq("uuid", flat_uuid).execute()
```

If you clear `flat.tenant_uuid` first, you lose the reference needed to clear `tenants.flat_uuid`. Read-then-clear is the correct order for unassign.

---

## 24. Row Level Security — Debugging and Auditing

RLS is a PostgreSQL feature that adds automatic WHERE clauses to every query based on `auth.uid()`. When RLS is misconfigured, queries silently return 0 rows or fail with "row-level security policy" errors.

**The diagnostic SQL queries (run in Supabase SQL Editor):**

```sql
-- Which tables have RLS enabled?
SELECT tablename, rowsecurity AS rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- What policies exist?
SELECT tablename, policyname, cmd AS operation, qual AS using_expr, with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- Does a specific column exist?
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'call_logs'
ORDER BY ordinal_position;
```

**The four RLS states and what they mean:**

| State | Risk | What to do |
|-------|------|-----------|
| `rls_on = false`, no policy | Open access — all rows visible to all users | Only acceptable for public reference tables (property_types) |
| `rls_on = true`, no policy | **All access blocked** — even authenticated queries return 0 rows | Add INSERT/SELECT/UPDATE/DELETE policies |
| `rls_on = true`, SELECT policy only | Users can read but not write | Intentional for subscription tables — Stripe webhook writes via service role |
| `rls_on = true`, `auth.uid()` policy | Normal multi-tenant isolation | Correct pattern for all user data tables |

**`USING` vs `WITH CHECK`:**
- `USING` — gates which rows can be read (SELECT), modified (UPDATE), or deleted (DELETE)
- `WITH CHECK` — gates what values can be written (INSERT, UPDATE)
- `FOR INSERT`: only `WITH CHECK` applies (no existing row to check against)
- `FOR SELECT`: only `USING` applies

**The ownership chain pattern for deeply nested data:**
```sql
-- tenants policy: can only see tenants whose flat is in your building
CREATE POLICY "managers can read own tenants"
ON tenants FOR SELECT TO authenticated
USING (
    flat_uuid IN (
        SELECT f.uuid FROM flats f
        JOIN buildings b ON f.building_id = b.id
        JOIN properties_list p ON b.property_id = p.id
        WHERE p.manager_id = auth.uid()
    )
);
```

Walk the FK chain to the table that has `manager_id`. Every table that is >1 hop from `properties_list` needs this chain.

**When RLS is wrong but tables are new:**
New tables created in Supabase have RLS enabled with no policies. All access is blocked by default. Use the service client with manual `manager_id` filtering as a temporary workaround while you write the proper policies.

---

## 25. Backend Performance — The Diagnostic Sequence

When a request feels slow, run through this sequence before touching code:

**Step 1: Confirm it's the backend (not the network)**
Open Chrome DevTools → Network tab → look at the request's green bar (TTFB — Time to First Byte). A large green bar is server processing time. A large blue bar is download time.

**Step 2: Rule out cold starts**
Free-tier Render services spin down after 15 minutes. A 30-second first response is a cold start, not a bug. Check if the server is on a paid plan.

**Step 3: Check the DB client setup**
This is the single most overlooked source of backend latency in this project:

```python
# SLOW — creates a new HTTP session on every request
def get_db():
    return create_client(url, key)  # NEW client = new connection pool = ~50-150ms overhead

# FAST — singleton created once at module import time
_client = create_client(url, key)
def get_db():
    return _client  # same object, ~0ms overhead
```

**Step 4: Check for N+1 queries**
A loop containing a DB call is almost always N+1:
```python
# N+1 — 1 query + N queries (one per appointment)
for apt in appointments:
    complaint = db.table("complaints").eq("id", apt["complaint_id"]).execute()  # ← N queries

# Fix — 2 queries total
ids = [apt["complaint_id"] for apt in appointments if apt.get("complaint_id")]
complaints = db.table("complaints").select("id, category").in_("id", ids).execute()
complaint_map = {c["id"]: c for c in complaints.data}
for apt in appointments:
    apt["category"] = complaint_map.get(apt.get("complaint_id"), {}).get("category")
```

**Step 5: Check indexes**
```sql
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('complaints', 'appointments', 'tenants')
ORDER BY tablename;
```

Run `EXPLAIN SELECT ...` on any slow query to see if it uses an index or does a seq scan.

**Step 6: Check payload size**
Does `GET /complaints` return every complaint ever with every field? `SELECT *` on large tables sends unnecessary data. Add `.select("uuid, flat_number, status, priority, created_at")` for list endpoints.

---

## 26. VAPI Integration — The Critical Patterns

**Pattern 1: Always return HTTP 200**
VAPI interprets any non-200 response as a server error and may retry or terminate the call. All VAPI tool endpoints must return 200, even for "not found" or "invalid" cases. Use a status field in the response body to communicate the outcome:

```python
# WRONG — raises HTTPException 404
if not flat.data:
    raise HTTPException(404, "Flat not found")

# CORRECT — returns 200 with status field
if not flat.data:
    return {"status": "invalid", "property_group_id": None, "datetime": now_ist()}
```

**Pattern 2: Normalize all inputs**
Phone numbers and flat numbers from voice calls may have inconsistent formatting. Always normalize before querying:

```python
flat_number = flat_number.strip().upper()   # "a 101" → "A 101"
phone_number = phone_number.strip()         # "+91 98765 43210" → "+919876543210"
```

**Pattern 3: The property_group_id resolution chain**
The complaint agent receives a call from a tenant who says their flat number. To scope the complaint to the right property group:

```
flat_number → flats.building_id → buildings.property_id → properties_list.id
```

The `verify-phone` endpoint resolves this chain and returns `property_group_id` in every response (even invalid ones — the VAPI agent schema may reference it).

**Pattern 4: Infrastructure as code for agent configs**
VAPI agent configurations are defined as Python dicts in `services/vapi_agent_config.py`. This means:
- Configs are version-controlled
- Different `backend_url` values work automatically per environment
- `property_group_id` can be baked into per-group agent system prompts programmatically
- Updates to 100 agents require a script, not 100 dashboard clicks

**Pattern 5: The `{{customer.number}}` template**
VAPI uses double-brace syntax in tool definitions for runtime values:
```json
"query": {
    "phone_number": "{{customer.number}}"
}
```
`customer.number` is the caller's E.164 phone number, captured by VAPI's telephony infrastructure. The agent uses this to verify the caller without asking "what's your phone number?" — which would be awkward and easily faked.

---

## 27. The Spec-to-Code Translation Process

When implementing a feature from a product spec:

**Step 1: Read with database normalization in mind**

| Spec phrase | Code question |
|-------------|--------------|
| "Each property has custom rules" | Is this a column (JSONB), separate table, or enum? |
| "Leads pipeline: contacted, toured, converted" | Is this a CHECK constraint or a separate table? |
| "Same number can serve multiple properties" | One VAPI assistant or many? What routing mechanism? |

**Step 2: Explore what already exists before building**

For any feature, read these files in order:
1. Backend route file — what endpoints exist?
2. `main.py` — what routers are registered?
3. `apiService.js` — what API calls exist?
4. Relevant frontend components — is the UI partially built?
5. DB schema — does the required column already exist?

Missing this step is how you duplicate code that already exists or break assumptions the codebase depends on.

**Step 3: Establish the correct build order**
```
DB schema changes → Backend routes → apiService.js → Frontend components → Navigation wiring
```

If you build frontend before backend, you're guessing at the API shape and will have to rebuild the frontend after the API shape is determined.

---

## 28. Integration Testing with Bash Scripts

For endpoint testing against a live server, bash + curl + jq is faster to write and easier to share than pytest:

```bash
# Test structure
echo "=== A1: verify-phone — valid phone ==="
RESPONSE=$(curl -s -X GET \
  "${BASE_URL}/flats/verify-phone?flat_number=${FLAT_NUMBER}&phone_number=${TENANT_PHONE}")

STATUS=$(echo "$RESPONSE" | jq -r '.status')
PG_ID=$(echo "$RESPONSE" | jq -r '.property_group_id')

assert_eq "A1 - status=valid"               "$STATUS"  "valid"
assert_ne "A1 - property_group_id non-null" "$PG_ID"   "null"
```

```bash
# The assert helper functions
assert_eq() {
    local label="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "[PASS] $label"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $label — expected '$expected', got '$actual'"
        FAIL=$((FAIL + 1))
    fi
}

assert_ne() {
    local label="$1" actual="$2" not_expected="$3"
    if [ "$actual" != "$not_expected" ]; then
        echo "[PASS] $label"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $label — should not be '$not_expected'"
        FAIL=$((FAIL + 1))
    fi
}
```

**The re-run checklist pattern:** After fixing bugs, write a checklist before re-running tests:
```markdown
## Re-run Checklist
- [x] Bug #1 — flats.py: get_db → get_service_db in verify_phone
- [x] Bug #2 — voice.py: Unicode → ASCII in all print statements
- [x] Bug #3 — leasing.py: Decimal → float in INSERT and PATCH
```

When you have multiple bugs to fix across files, you WILL miss one without a written checklist. The list converts "I think I got everything" into a verifiable record.

**A "SKIP" is not "PASS":** In a test report, a SKIP means "test was not run, usually because a dependency failed." A cascading skip (tests C4–C10 skipped because C3 failed) means the root cause is in the first failing test. Fix that, then re-run — the cascade often resolves itself.

---

## 29. Deployment — The Production Configuration Checklist

The most common class of production bugs is "the code is correct but the environment is wrong." Always run through this before declaring a feature deployed:

**Google OAuth:**
```
□ Google Console → Authorized JS Origins: the domain where signInWithOAuth() runs (NOT the backend URL)
□ Google Console → Authorized Redirect URIs: https://<project>.supabase.co/auth/v1/callback
□ Supabase → Auth → URL Configuration → Site URL: your production frontend URL
□ Supabase → Auth → Redirect URLs: all valid redirect destinations (exact match, no trailing slash)
```

**Environment Variables:**
```
□ .env files are for local development only — never trust them in production
□ Production values must be set in Vercel/Netlify/Render environment variable UI
□ VITE_API_URL on Netlify must be the Render backend URL, not localhost:8000
□ NEXT_PUBLIC_FRONTEND_URL on Vercel must be the Netlify CRM URL, not localhost:5173
```

**SPA Routing (Netlify):**
```
□ frontend/public/_redirects exists with: /*  /index.html  200
□ Without this, browser refresh on any non-root URL returns Netlify's 404
```

**The exact-match requirement for Supabase redirect URLs:**
`https://www.leadpipe.ca/auth/callback` ≠ `https://leadpipe.ca/auth/callback` (www matters) ≠ `https://www.leadpipe.ca/auth/callback/` (trailing slash matters). Run `window.location.origin` in the browser console and copy-paste that exact string into Supabase's redirect URL list.

---

## 30. The Systematic Debugging Method

When something breaks, run this sequence before touching code:

### Step 1: State the symptom precisely
"It doesn't work" is not a symptom. These are:
- "After clicking Next on step 1, the tooltip disappears and the overlay stays dark permanently"
- "VAPI endpoint returns status=invalid even when the flat and phone are correct"
- "The SMS sends on cancel via UI but not via chatbot"

The precise statement reveals which layer to investigate.

### Step 2: Ask "whose code is running and whose isn't?"
Add a `console.log` or `print()` at the entry point. If it fires → the issue is logic. If it doesn't fire → the issue is connection (wrong route, wrong prop, wrong event name, wrong URL).

### Step 3: Rule out the obvious
Before reading code:
- Is the server running? (`curl -s http://localhost:8000/health`)
- Is the right environment active? (correct `.env`, correct npm workspace)
- Is this a cold start? (first request after server idle)
- Is this a Windows encoding issue? (check `print()` statements for non-ASCII)

### Step 4: Fix one thing at a time
Multiple broken things often coexist. Fix them in order from most fundamental to least:
1. Is the callback connected at all? (wrong prop name, wrong event name)
2. Does the data reach the function? (missing field in `select()`)
3. Does the function execute? (missing import, wrong dependency)
4. Does the side effect fire? (notification, refresh, analytics)

If you attempt to fix all four simultaneously, you cannot tell which fix resolved which symptom.

### Step 5: Verify against the original symptom
After each fix, reproduce the exact original test case. "I think I fixed it" is not evidence. Run the action that was broken and observe the outcome.

---

## 31. The Most Dangerous Silent Failures

These bugs produce no error — they just silently do nothing. They are the hardest to notice because the code appears to work.

| Silent failure | Why it's silent | How to detect |
|----------------|----------------|---------------|
| SMS not sending | `notify_tenant_appointment()` catches all exceptions | Check backend logs for "notify failed" |
| VAPI endpoint returning wrong data | RLS returns 0 rows (no error, just empty) | Check if DB client is anon vs service role |
| `flat_uuid` not in `select()` | `.get("flat_uuid")` returns `None`, notification skipped | Audit `select()` fields vs what the call needs |
| Chatbot tool not called | LLM chose not to call it | Check tool definition and system prompt capability description |
| `onEvent` prop wrong name | Joyride receives unknown prop, ignores it | Grep the dist for the prop name |
| Cache from old deployment | Browser serves stale JS | Open Network tab with "Disable cache" checked |
| `localStorage` keyed by origin, not user | User B sees User A's state | Scope key by user ID: `key-${user.id}` |
| Background task failing on server restart | In-process task queue — doesn't survive restarts | Use Celery/Redis for critical background work |

---

## 32. The Senior Dev Mindset — Principles Synthesized Across All Sessions

**1. Features are never isolated.**
A "Rent Tab" requires: backend endpoint, API service method, React component, sidebar nav item, App.jsx routing, DB migration, and possibly an RLS policy. Before writing code, draw the full map of what needs to change.

**2. Your code runs in an environment, not a vacuum.**
A function that works correctly can still fail because: the caller has no JWT, the DB table has no RLS policy, the Windows console can't encode the character you printed, or the VAPI webhook retried because your response was too slow.

**3. Every early return must leave the system in a clean state.**
If a function starts a loading state, opens an overlay, or sets a flag to `true`, every code path — including every early `return` — must reset that state. A dark Joyride overlay that persists after the tour logic exits is the canonical example.

**4. The installed version is the truth, not the documentation.**
Docs describe the version they were written for. The compiled dist file is the ground truth for what props, events, and behaviors exist in the version you actually installed. Grep the dist.

**5. localStorage is per-origin, not per-user.**
Any data that differs between users — progress, drafts, preferences — must be keyed by user ID. Unscoped keys are shared across all users on the same device.

**6. Notifications must fire on all code paths or they're broken.**
If there are four ways to cancel an appointment, the SMS must fire on all four. Three out of four is wrong. Map every entry point before shipping.

**7. Use the right DB client for the right caller.**
Authenticated users → `get_authenticated_db` (RLS enforced).
Webhooks, VAPI, Stripe, background tasks → `get_service_db` (RLS bypassed, manual scope filtering).

**8. The diagnostic question sequence:**
   a. What is the precise symptom?
   b. Who calls this, and do they have a JWT?
   c. What does the DB actually return? (verify in Supabase SQL editor)
   d. What does the server log say? (always read the stack trace before guessing)
   e. Is this a code bug or an environment bug?

**9. Build complete features, not happy-path features.**
A feature is complete when it works across all code paths, is consistent across all layers (DB/API/frontend), handles the edge cases (already-cancelled, no phone number, null flat_uuid), and cleans up after itself (removes unused imports, keeps all three layers in sync).

**10. Measure before optimizing.**
A 2400ms green bar in DevTools tells you the problem is server-side TTFB. A 2400ms blue bar is a download size problem. An N+1 query shows as: endpoint is slow but returns small amounts of data. Check the actual numbers before writing a single line of optimization.

---

**FINAL MANDATE — UPDATED:**
The original mandate said "fix the loopback in `voice.py`." That loopback has been fixed. The new mandate is broader:

Before shipping any feature, ask five questions:
1. *Who calls this, and do they have a JWT?* (infrastructure category)
2. *What does my code do on all entry points?* (all-code-paths principle)
3. *Are the DB constraint, Pydantic enum, and frontend constants in sync?* (three-layer rule)
4. *Did I fetch every field my new logic needs?* (silent-failure prevention)
5. *What happens on Windows? In production? After a server restart?* (environment assumptions)

A senior engineer is not someone who writes perfect code. They are someone who asks these questions every time and doesn't ship until they have answers.

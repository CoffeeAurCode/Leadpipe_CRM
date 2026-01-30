# Tenant Management MVP

AI-powered complaint management system with voice call integration using Vapi.ai and FastAPI.

## Tech Stack

- **Framework**: FastAPI
- **Language**: Python 3.10+
- **ORM**: SQLAlchemy (async)
- **Database**: PostgreSQL
- **Authentication**: JWT (python-jose)
- **Password Hashing**: passlib with bcrypt
- **Voice AI**: Vapi.ai (STT + voice calls)
- **AI Extraction**: Groq (Llama 3.1-8b-instant)
- **Database Migrations**: Alembic
- **HTTP Client**: httpx (async)

## Project Structure

```
backend/
├── alembic/
│   ├── versions/          # Database migration files
│   └── env.py             # Alembic configuration
├── app/
│   ├── ai/
│   │   ├── extractor.py   # AI complaint extraction (Groq)
│   │   └── validator.py   # Complaint data validation
│   ├── config.py          # Environment configuration
│   ├── db/
│   │   ├── base.py        # SQLAlchemy declarative base
│   │   ├── models.py      # Database models (Complaint, CallLog, etc.)
│   │   └── session.py     # Async database session
│   ├── routes/
│   │   ├── complaints.py  # Complaint CRUD endpoints
│   │   └── voice.py       # Vapi webhook handler
│   ├── schemas/
│   │   └── complaint.py   # Pydantic validation schemas
│   └── main.py            # FastAPI application
├── alembic.ini            # Alembic configuration
├── .env                   # Environment variables (not in git)
├── .env.example           # Environment template
└── requirement.txt        # Python dependencies
```

## Features

### Voice Complaint Intake
- **Vapi.ai Integration**: Voice calls with speech-to-text
- **Real-time Webhooks**: Event-driven architecture
- **AI Extraction**: Automatic complaint field extraction using Groq
- **Idempotent Processing**: Handles duplicate webhook events safely
- **Call Audit Trail**: All calls logged in `call_logs` table

### Complaint Management
- Create, read, update complaints
- Status tracking (pending, in-progress, resolved, closed)
- Flat number-based filing (no tenant lookup required)
- Source tracking (voice, web, manual)

### Database
- **PostgreSQL** with async SQLAlchemy
- **Alembic migrations** for schema versioning
- **Models**: User, Unit, Tenant, Complaint, CallLog

## Setup

### 1. Create Virtual Environment

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
```

### 2. Install Dependencies

```bash
pip install -r requirement.txt
```

**Key Dependencies:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy[asyncio]` - Async ORM
- `asyncpg` - PostgreSQL async driver
- `psycopg2-binary` - PostgreSQL sync driver (for migrations)
- `alembic` - Database migrations
- `groq` - AI extraction (free Llama 3.1)
- `httpx` - Async HTTP client
- `python-jose[cryptography]` - JWT
- `passlib[bcrypt]` - Password hashing

### 3. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/tenant_management_db

# Security
SECRET_KEY=your-secret-key-here

# AI
GROQ_API_KEY=your-groq-api-key  # Get from console.groq.com (free)
```

### 4. Run Database Migrations

```bash
# Create initial migration (if not exists)
alembic revision --autogenerate -m "init migration"

# Apply migrations
alembic upgrade head

# Check current version
alembic current
```

## Running the Server

### Development Server

```bash
cd backend
uvicorn app.main:app --reload
```

The server will start at `http://localhost:8000`

### With ngrok (for Vapi webhook testing)

```bash
# Terminal 1: Start backend
uvicorn app.main:app --reload

# Terminal 2: Start ngrok tunnel
ngrok http 8000
```

Copy the ngrok URL and configure it in your Vapi.ai dashboard as the webhook endpoint:
```
https://your-ngrok-url.ngrok.io/voice/webhook
```

## API Endpoints

### Complaints

- **Create Complaint**: `POST /complaints`
- **Get All Complaints**: `GET /complaints`
- **Get Complaint by ID**: `GET /complaints/{id}`
- **Update Complaint**: `PATCH /complaints/{id}`

### Voice Webhook

- **Vapi Webhook**: `POST /voice/webhook`
  - Receives Vapi.ai webhook events
  - Filters for final events (`tool-calls`, `end-of-call-report`)
  - Extracts complaint data from user confirmation
  - Creates CallLog (always) and Complaint (if confirmed)
  - Returns 200 OK (prevents Vapi retry storms)

### Health Check

```bash
curl http://localhost:8000/
```

Expected response:
```json
{"status": "Backend running"}
```

## Testing

### Interactive API Documentation

**Swagger UI:**
```
http://localhost:8000/docs
```

**ReDoc:**
```
http://localhost:8000/redoc
```

### Test Voice Webhook Locally

1. Start server: `uvicorn app.main:app --reload`
2. Start ngrok: `ngrok http 8000`
3. Configure Vapi webhook URL: `https://your-url.ngrok.io/voice/webhook`
4. Make a test call via Vapi
5. Check logs for webhook events
6. Verify database:
   ```sql
   SELECT * FROM call_logs ORDER BY created_at DESC LIMIT 5;
   SELECT * FROM complaints ORDER BY created_at DESC LIMIT 5;
   ```

## Database Schema

### CallLog Table
Tracks all voice calls (audit trail):
- `call_id` (unique) - Vapi call identifier
- `phone_number` - Caller's phone
- `transcript` - Full conversation transcript
- `raw_event_type` - Vapi event type
- `complaint_status` - Status: abandoned, incomplete, pending, created, failed
- `complaint_id` - Foreign key to Complaint (nullable)
- `created_at` - Auto-populated timestamp

### Complaint Table
Stores complaint records:
- `flat_number` - Apartment/unit number
- `category` - Complaint category
- `priority` - low, medium, high
- `description` - Detailed complaint text
- `status` - pending, in-progress, resolved, closed
- `source` - voice, web, manual
- `tenant_id` - Foreign key (nullable)

## Architecture Notes

### Event-Driven Webhook Pattern

The voice webhook uses an **event-stream model**:
- Vapi sends 10-50 events per call
- Only `tool-calls` and `end-of-call-report` are processed
- All other events return `{"status": "ignored"}`
- Always returns HTTP 200 (prevents Vapi failures)

### Idempotency

- Uses `call_id` as idempotency key
- Checks for existing CallLog before creating
- Prevents duplicate complaints on retry/multiple events
- Safe to process same event multiple times

### Error Handling Philosophy

```
Transport success (200 OK) ≠ Business success (complaint created)
```

- Errors are **logged**, not **thrown**
- Database state is **source of truth**
- Webhook always returns 200 to prevent retry storms
- Failed operations saved with `status="failed"` for investigation

## Development Guidelines

- **Event filtering first**: Filter by `message.type` before extracting data
- **Defensive extraction**: Use fallback chains for payload parsing
- **Explicit logging**: Log every decision point and external call
- **Idempotent operations**: All webhook handlers must be safe to retry
- **CallLog-first**: Always create CallLog, even if complaint fails

## Next Steps

- [ ] Replace internal HTTP calls with direct service functions
- [ ] Add comprehensive unit tests
- [ ] Add integration tests for webhook flow
- [ ] Implement monitoring and alerting
- [ ] Add retry logic for Groq API failures
- [ ] Production deployment (Docker + gunicorn)
- [ ] Add tenant association async job

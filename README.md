# Tenant Management MVP

AI-powered complaint management system built with FastAPI.

## Tech Stack

- **Framework**: FastAPI
- **Language**: Python 3.10+
- **ORM**: SQLAlchemy (async)
- **Database**: PostgreSQL
- **Authentication**: JWT (python-jose)
- **Password Hashing**: passlib with bcrypt

## Project Structure

```
backend/
├── app/
│   ├── config.py           # Environment configuration
│   ├── db/
│   │   ├── models.py       # SQLAlchemy models
│   │   └── session.py      # Database session
│   ├── routes/
│   │   └── complaints.py   # Complaint endpoints
│   ├── schemas/
│   │   └── complaint.py    # Pydantic schemas
│   └── main.py             # FastAPI application
├── .env                    # Environment variables
├── .env.example            # Environment template
└── requirement.txt         # Python dependencies
```

## Setup

### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
```

### 2. Install Dependencies

```bash
pip install -r requirement.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and update with your database credentials:

```bash
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/tenant_management_db
SECRET_KEY=your-secret-key-here
```

## Running the Server

```bash
uvicorn app.main:app --reload
```

The server will start at `http://localhost:8000`

## Testing

### Health Check

```bash
curl http://localhost:8000/
```

Expected response:
```json
{"status": "Backend running"}
```

### Complaints Endpoints

- **Create Complaint**: `POST /complaints/`
- **Get All Complaints**: `GET /complaints/`
- **Get Complaint by ID**: `GET /complaints/{id}`
- **Update Complaint**: `PATCH /complaints/{id}`

### Swagger UI

Access interactive API documentation at:
```
http://localhost:8000/docs
```

Alternative documentation (ReDoc):
```
http://localhost:8000/redoc
```
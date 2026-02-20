# Tenant Management MVP

An AI-powered tenant complaint management system featuring voice call integration via **Vapi.ai**, automated data extraction with **Groq (Llama 3.1)**, a modern **React dashboard**, and real-time manager notifications.

## 🚀 Core Features

### 🎙️ AI Voice Intake
- **Voice Call Integration**: Powered by Vapi.ai for natural language conversation.
- **Automated Extraction**: Uses Groq (Llama 3.1-8b) to extract flat numbers, categories, priorities, and descriptions from voice transcripts.
- **Smart Scheduling**: AI can suggest and record maintenance appointment times.
- **Idempotent Webhooks**: Robust handler for Vapi events (tool-calls, end-of-call) that prevents duplicate entries.

### 📊 Manager Dashboard (LeadPipe UI)
- **Bento Grid Layout**: Visually rich dashboard with quick stats and recent activity.
- **Complaint Management**: View, filter, and update statuses (Pending, In-Progress, Resolved, Closed).
- **Property View**: Track occupancy, unit details, and tenant associations.
- **Real-time Updates**: Auto-refresh functionality to keep the data current.

### 🔔 Smart Notifications
- **Email Alerts**: Instant email notifications to managers via SendGrid when new complaints or appointments are booked.
- **SMS Alerts**: (Ready for Twilio integration) to ensure urgent issues are handled immediately.
- **Background Processing**: Notifications are handled asynchronously to keep the API responsive.

### 🏗️ Property Management
- **Unit Tracking**: Manage flats, floors, and occupancy status.
- **Tenant Links**: Associate complaints directly with units and tenants.

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Asynchronous)
- **Database**: PostgreSQL (with Supabase/Direct SQL)
- **ORM**: SQLAlchemy (Async)
- **Migrations**: Alembic
- **AI**: Groq (Llama 3.1), Vapi.ai (Voice)
- **Notifications**: SendGrid (Email)

### Frontend
- **Framework**: React (Vite)
- **Styling**: Tailwind CSS (Custom Design System)
- **Icons**: Lucide React
- **Animations**: Framer Motion / CSS Transitions

---

## 📂 Project Structure

```text
.
├── backend/                # FastAPI Application
│   ├── app/
│   │   ├── ai/            # Extraction and validation logic
│   │   ├── db/            # Models and DB session management
│   │   ├── integrations/   # SendGrid, Twilio, external APIs
│   │   ├── routes/        # API Endpoints (Complaints, Voice, Properties)
│   │   ├── schemas/       # Pydantic models
│   │   └── main.py        # Entry point
│   ├── alembic/           # Migrations
│   └── .env               # Secrets
├── frontend/               # React Application
│   ├── src/
│   │   ├── components/    # UI Components (StatsCards, Lists, Modals)
│   │   ├── layouts/       # Dashboard and App layouts
│   │   ├── pages/         # Dashboard, Complaints, Properties
│   │   └── services/      # API clients
│   └── tailwind.config.js # Design tokens
└── docs/                   # Guides and analysis reports
```

---

## 🧭 Codebase Rundown (For Developers)

### 1. The Call Flow
1. **User calls** the Vapi phone number.
2. **Vapi** processes speech and hits the `/voice/webhook` endpoint.
3. The **Webhook Handler** (`routes/voice.py`) filters for specific events.
4. If a complaint is confirmed by the user, the AI extracts data via `ai/extractor.py`.
5. A **Complaint** and **CallLog** are created in the database.
6. A **Background Task** triggers the `EmailClient` to notify the manager.

### 2. Data Persistence
- Core models are in `app/db/models.py`.
- **CallLog**: Acts as an audit trail for every single interaction.
- **Complaint**: The primary entity representing a tenant issue.
- **Flat**: Represents a physical unit, used for the Properties view.

### 3. Frontend Architecture
- Uses a **Bento Grid** design system for the dashboard.
- **Tailwind CSS** is used for all styling with a custom palette (Zinc/Slate base with primary action colors).
- Data is fetched via hooks in `services/` and managed locally in components.

---

## ⚙️ Setup & Installation

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirement.txt
cp .env.example .env       # Configure your keys
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🛡️ Architecture Philosophy
- **Defensive Webhooks**: Always return `200 OK` to Vapi to prevent retry loops; log failures internally.
- **Idempotency**: Use `call_id` to ensure one call never creates two complaints.
- **UI/UX Priority**: The dashboard is designed to be "LeadPipe" aesthetic—premium, clean, and interactive.

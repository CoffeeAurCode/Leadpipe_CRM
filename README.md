# Tenant Management MVP

An AI-powered property and tenant management system with voice call intake, an AI chat assistant, automated SMS notifications, and a full-featured React dashboard.

---

## Features

### AI Chat Assistant
- Floating chatbot in the dashboard powered by **OpenAI gpt-4o-mini**
- Natural language interface for all management tasks — no need to navigate the UI
- Renders responses as rich markdown (bold, lists, code)
- Full tool suite:
  - Add / delete properties, buildings, and units
  - Look up tenant details by name, phone, or flat number
  - View, reschedule, cancel, and mark appointments (scheduled → attended)
  - View and filter complaints by flat or status
  - Aware of today's date — understands "tomorrow", "next Monday", etc.
- Always asks for confirmation before any write or delete operation
- SMS sent to tenant automatically after every chatbot action that changes an appointment

### Voice Call Intake (VAPI)
- Tenants call a phone number powered by **Vapi.ai**
- Voice agent verifies the caller's flat, logs the complaint, and books an appointment
- Backend endpoints designed for VAPI: always return HTTP 200, use boolean `exists` field for AI branching
- Appointment reschedule and cancel also available via voice

### Appointment Management
- Full calendar view with month navigation and a slide-out day panel
- Click any appointment in the panel to open its detail modal
- Edit date/time, notes, and status (Scheduled / Attended / Cancelled) inline
- Three-status system: `scheduled`, `attended`, `cancelled`
- SMS notification sent to tenant on every status change, reschedule, or cancellation — regardless of whether the change was made via the UI, voice agent, or chatbot

### Complaint Management
- Dedicated Complaints page with category and status filters
- Complaint cards with priority badges (High / Medium / Low)
- Click any complaint to open a detail/edit modal
- Linked complaints shown on their associated appointment detail modal

### Property Hierarchy
- Three-level structure: **Properties → Buildings → Units**
- Per-building cover photo upload (stored in Supabase Storage)
- Tenant assignment per unit with contact details

### Dashboard
- KPI cards: total complaints, pending, in-progress, today's appointments
- Click "Daily Tasks" KPI to see today's appointments list; click any appointment to open its detail modal
- Charts: complaint trends, status donut, category breakdown, appointments-per-day bar

### Notifications
- **Tenant SMS** (Twilio): sent on appointment created, rescheduled, cancelled, attended, or reactivated
- **Manager SMS** (Twilio): sent when a new appointment is scheduled (feature-flag controlled per unit)
- **Manager Email**: HTML email with full complaint + tenant details on new appointment (feature-flag controlled)
- All notifications run as FastAPI background tasks — never block the HTTP response

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | FastAPI (Python) |
| Database | Supabase (PostgreSQL) via Supabase Python SDK |
| AI chatbot | OpenAI gpt-4o-mini |
| Voice AI | Vapi.ai |
| SMS | Twilio |
| File storage | Supabase Storage |
| Frontend framework | React + Vite |
| Styling | Tailwind CSS |
| Animations | Framer Motion |
| Icons | Lucide React |
| Date handling | date-fns |
| Markdown rendering | react-markdown |

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   └── chatbot.py          # OpenAI tool-calling chatbot logic
│   │   ├── db/
│   │   │   └── session.py          # Supabase client (get_db dependency)
│   │   ├── integrations/
│   │   │   ├── twilio_client.py    # SMS sending
│   │   │   └── email_client.py     # Email sending
│   │   ├── routes/
│   │   │   ├── appointments.py     # CRUD + VAPI tool endpoints
│   │   │   ├── chat.py             # POST /chat (AI chatbot)
│   │   │   ├── complaints.py
│   │   │   ├── flats.py            # POST /flats/verify-phone (VAPI)
│   │   │   ├── upload.py           # Building cover photo upload
│   │   │   ├── voice.py            # VAPI webhook handler
│   │   │   └── ...
│   │   ├── schemas/
│   │   │   └── appointment.py      # AppointmentStatus enum (scheduled/attended/cancelled)
│   │   ├── services/
│   │   │   └── notifications.py    # notify_tenant_appointment(), notify_manager_...()
│   │   ├── config.py               # Settings loaded from .env
│   │   └── main.py                 # Router registration (no /api prefix)
│   ├── migrations/                 # Numbered SQL migration files
│   └── requirement.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── dashboard/          # KPI cards, charts, DailyTasksModal
│   │   │   ├── AppointmentDetailModal.jsx
│   │   │   ├── BentoDashboard.jsx
│   │   │   ├── CalendarView.jsx
│   │   │   ├── Chatbot.jsx         # Floating AI chat assistant
│   │   │   ├── ComplaintsPage.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   └── TopBar.jsx
│   │   ├── constants/
│   │   │   └── status.js           # APPOINTMENT_STATUS, STATUS_CONFIG (single source of truth)
│   │   ├── services/
│   │   │   └── apiService.js       # ALL HTTP calls live here — no inline fetch in components
│   │   └── App.jsx                 # Root: view-based routing, data loading, refresh events
│   └── package.json
│
├── chat_ability.md                 # Full list of chatbot capabilities with example prompts
├── LEARNING_GUIDE_SESSION_16.md    # Session guide: chatbot implementation, VAPI design
├── LEARNING_GUIDE_SESSION_17.md    # Session guide: notifications, RLS, status layers, modals
└── README.md
```

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase project (free tier works)
- OpenAI API key
- Twilio account (for SMS)
- Vapi.ai account (for voice, optional)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirement.txt
cp .env.example .env             # fill in your keys
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Environment Variables (`.env`)

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key   # required for file uploads

# OpenAI (chatbot)
OPEN_AI_API=sk-proj-...

# Twilio (SMS)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
MANAGER_PHONE=+91...             # receives manager notifications

# Email (optional)
SENDGRID_API_KEY=SG....
FROM_EMAIL=notifications@yourdomain.com
MANAGER_EMAIL=manager@yourdomain.com
```

---

## Key Design Decisions

**No `/api` prefix.** All routes are registered directly: `/appointments`, `/chat`, `/tenants`. No global prefix.

**Supabase SDK, not SQLAlchemy.** All DB access uses `db.table("x").select().execute()` — no ORM, no migrations library. Schema changes are managed as numbered SQL files in `backend/migrations/`.

**Single source of truth for status values.** `frontend/src/constants/status.js` defines all status values and their display config. Never hardcode status strings in components.

**All HTTP calls in `apiService.js`.** No inline `fetch()` inside React components. Every API call goes through `frontend/src/services/apiService.js`.

**Cross-component refresh via custom events.** When the chatbot or another component changes data, it dispatches `window.dispatchEvent(new Event('refresh-appointments'))`. `App.jsx` listens and reloads.

**VAPI endpoints always return HTTP 200.** Voice agent endpoints never return 404 or 500 — they always return 200 with a boolean `exists` or `available` field so the AI can branch correctly without the conversation breaking.

**Service role key only for storage.** The anon key is used for all DB table operations (RLS applies). A separate service role client is created only for Supabase Storage uploads, which require bypassing RLS.

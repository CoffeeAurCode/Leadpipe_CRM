# Learning Guide — Session 16
## Topic: Auditing Implementation Plans, Building an AI Chatbot, and VAPI Webhook Design

> **Audience:** A junior developer or intern joining the project mid-stream.
> **Goal:** By the end of this guide you should be able to (a) audit a feature plan before coding it, (b) build a Groq-powered chatbot with tool calling end-to-end, (c) design VAPI-compatible webhook endpoints, and (d) debug live LLM issues.

---

## Table of Contents

1. [Project Architecture Overview](#1-project-architecture-overview)
2. [Part 1 — Auditing an Implementation Plan](#2-part-1--auditing-an-implementation-plan)
3. [Part 2 — Building the AI Chatbot (Backend)](#3-part-2--building-the-ai-chatbot-backend)
4. [Part 3 — Building the AI Chatbot (Frontend)](#4-part-3--building-the-ai-chatbot-frontend)
5. [Part 4 — Live Debugging Session](#5-part-4--live-debugging-session)
6. [Part 5 — VAPI Webhook Design](#6-part-5--vapi-webhook-design)
7. [Commands Reference](#7-commands-reference)
8. [Industry Best Practices Applied](#8-industry-best-practices-applied)
9. [Resources and Further Reading](#9-resources-and-further-reading)

---

## 1. Project Architecture Overview

Before making any changes, always understand the existing system. This project is a **Tenant Management MVP**:

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                      │
│  Vite + React + TailwindCSS + Framer Motion             │
│  localhost:5173                                          │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/JSON
┌──────────────────────▼──────────────────────────────────┐
│                    BACKEND (FastAPI)                      │
│  Python 3.11 + FastAPI + Pydantic + Supabase SDK         │
│  localhost:8000                                          │
└──────────────────────┬──────────────────────────────────┘
                       │ Supabase SDK (not SQL directly)
┌──────────────────────▼──────────────────────────────────┐
│               DATABASE (Supabase / PostgreSQL)            │
│  Tables: flats, tenants, buildings, appointments,        │
│          complaints, rents, property_groups              │
└──────────────────────────────────────────────────────────┘
                       │ External APIs
┌──────────────────────▼──────────────────────────────────┐
│              GROQ API (LLM Inference)                    │
│  Model: llama-3.3-70b-versatile                         │
│  Used for: AI chatbot tool calling                       │
└──────────────────────────────────────────────────────────┘
```

**Key files to know:**
- `backend/app/main.py` — FastAPI app, registers all routers
- `backend/app/config.py` — Settings loaded from `.env`
- `backend/app/routes/` — One file per resource (appointments.py, tenants.py, etc.)
- `backend/app/ai/chatbot.py` — Groq LLM chatbot logic
- `frontend/src/App.jsx` — Root React component
- `frontend/src/services/apiService.js` — ALL HTTP calls to backend live here
- `frontend/src/components/` — UI components

---

## 2. Part 1 — Auditing an Implementation Plan

### Why Audit Before Coding?

Writing code based on a flawed plan costs 10× more to fix than fixing the plan first. Senior engineers always do a "pre-mortem" — reading the plan and asking: *"What could break?"*

### The 5-Category Audit Framework

Organize your findings into severity levels:

| Severity | Meaning | Example |
|----------|---------|---------|
| **CRITICAL** | Will break at runtime, wrong assumption | Wrong URL prefix |
| **HIGH** | Production risk, security or data integrity | No auth on destructive endpoint |
| **MEDIUM** | Correctness / maintainability | Signature mismatch with existing API |
| **LOW** | Informational / polish | Package already installed |

### What We Found and Fixed (Real Example)

The plan was for a Groq-powered chatbot. Here are the 19 issues we found:

#### CRITICAL Issues Found

**Issue 1: Wrong URL Prefix**
```
Plan said:   POST /api/chat
Reality:     Every other route is /tenants, /appointments, /buildings (no /api prefix)
Fix:         Register as POST /chat  to match existing convention
```

**How to spot this:** Always look at `main.py` to see how existing routers are registered:
```python
# backend/app/main.py
app.include_router(tenants.router)      # prefix="/tenants"
app.include_router(appointments.router) # prefix="/appointments"
# Therefore chatbot should be:
app.include_router(chat.router)         # prefix="/chat"  ← not /api/chat
```

**Issue 2: FAB Button Position Conflicts with Sidebar**
```
Plan said:   Position chatbot FAB at bottom-4 left-4
Reality:     App has a fixed sidebar on the LEFT side
Fix:         Use bottom-4 right-4 (bottom-right is also the UX convention for chat)
```

**How to spot this:** Before adding any fixed/absolute-positioned UI element, look at `App.jsx` or the main layout to see what else is anchored.

**Issue 3: No Recursion Guard on Tool Call Loop**
```
Plan said:   "Recursively handles tool calls if multiple turns are required"
Reality:     If LLM keeps calling a tool expecting different output → infinite loop
Fix:         Add MAX_TOOL_CALL_TURNS = 5 hard cap
```

```python
# Wrong pattern (infinite recursion risk):
while True:
    response = call_llm()
    if no_tool_calls: return response
    execute_tools()

# Correct pattern:
MAX_TOOL_CALL_TURNS = 5
for _ in range(MAX_TOOL_CALL_TURNS):
    response = call_llm()
    if no_tool_calls: return response
    execute_tools()
return "Reached max steps. Please rephrase."
```

**Issue 4: Tool Calls Non-Existent DB Tables**
```
Plan said:   Tool "add_new_property"
Reality:     No "properties" table to INSERT into. Data hierarchy is:
             PropertyGroup → Building → Flat  (three separate tables)
Fix:         Replace with add_new_unit (inserts into flats) and
             add_new_building (inserts into buildings)
```

**How to spot this:** Always map every tool to a concrete table + SQL operation before approving the plan.

**Issue 5: No System Prompt**
```
Plan said:   (nothing about system prompt)
Reality:     Without a system prompt, LLM has no persona, no behavioral rules
             It will give generic off-topic responses
Fix:         Inject a system message at position 0 of every Groq API call
```

#### HIGH Issues Found

**Issue 6: No DB Dependency Injection in Tool Executor**
```
Plan said:   "Tool execution maps to existing CRUD operations"
Reality:     All CRUD logic is INSIDE route handlers — there are no standalone
             service functions. The tool executor needs a DB client.
Fix:         Route handler receives db: Client = Depends(get_db) and passes it
             explicitly to the tool executor function.
```

```python
# Wrong — chatbot.py can't call get_db() itself outside a request context
def execute_tool(tool_name, args):
    db = get_db()  # ← This doesn't work outside FastAPI dependency context

# Correct — db is passed in from the route handler
def execute_tool(tool_name, args, db: Client):  # ← db is injected
    ...

@router.post("")
async def chat_endpoint(request, db: Client = Depends(get_db)):
    reply = chatbot.run_chat(messages, db)  # ← pass it through
```

**Issue 7: Context Window Will Overflow**
```
Problem:     Frontend sends FULL chat history every message.
             llama-3.3-70b has ~128K context, but tool schemas alone cost ~500 tokens.
             After ~100 exchanges the conversation can get expensive and slow.
Fix:         Backend truncates to last 10 messages before sending to Groq:
```

```python
truncated = messages[-10:] if len(messages) > 10 else messages
full_messages = [system_message] + truncated
```

**Issue 8: API Calls in Component Bypass apiService.js**
```
Plan said:   Chatbot.jsx makes inline fetch() calls directly
Reality:     EVERY API call in this project goes through apiService.js
             This is for consistency, easy base URL changes, error handling
Fix:         Add sendChatMessage() to apiService.js, import it in Chatbot.jsx
```

#### How to Write Up Your Audit

Format each finding as:
1. **What the plan says**
2. **What reality is** (check the actual code)
3. **Why it's a problem**
4. **Concrete fix**

This gives the team clear, actionable items instead of vague "this might be wrong."

---

## 3. Part 2 — Building the AI Chatbot (Backend)

### Step 1: Add the API Key to Config

Every external API key goes in `config.py` loaded from `.env`. Never hardcode.

```python
# backend/app/config.py
import os

class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")  # ← add this
    # ... other settings

settings = Settings()
```

```bash
# .env file (never commit this to git)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Get your Groq API key at: https://console.groq.com/keys

### Step 2: Create the Chatbot Module

**File:** `backend/app/ai/chatbot.py`

The full pattern for Groq tool calling:

```
User message
    ↓
Groq API (with tools schema)
    ↓
Response has tool_calls?
    YES → execute tool → append tool result → call Groq again
    NO  → return final answer to user
```

#### 2a. Define the System Prompt

The system prompt is the LLM's "job description." It must:
- Define the role ("You are a property management assistant")
- State the rules ("Always ask for confirmation before write operations")
- Inject dynamic context (today's date)

```python
_SYSTEM_PROMPT_BASE = """You are a property management assistant for a tenant management dashboard.
You help managers add units, add buildings, retrieve tenant information, and check or reschedule appointments.
Be concise and professional.

Rules you must always follow:
- Before performing any write operation (add, update, reschedule), always ask the user for explicit confirmation first.
- When rescheduling, use ONLY the appointment ID that the user explicitly stated. If that appointment is not found, tell the user it does not exist — do NOT substitute a different appointment ID.
- When adding a unit, look up the building by the name the user provides. Do not ask for a building ID.
- Today's date is {today}. Use this when the user says "today", "tomorrow", "yesterday", etc."""
```

**Why `{today}` placeholder?** The system prompt is defined at module load time (once, when Python imports the file). If you hardcode the date there, it will always say the same date. Instead, you inject it dynamically at request time:

```python
def run_chat(messages: list, db: Client) -> str:
    today = datetime.now().strftime("%A, %B %d, %Y")
    # e.g. "Monday, March 16, 2026"
    system_content = _SYSTEM_PROMPT_BASE.format(today=today)
```

#### 2b. Define Tool Schemas

Groq (and OpenAI) use a JSON Schema format to describe what tools the LLM can call. Each tool is an object with:

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_new_building",          # Python function name to call
            "description": "Add a new building...", # LLM reads this to decide when to call it
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the building"
                    },
                    "address": {
                        "type": "string",
                        "description": "The full address of the building"
                    }
                },
                "required": ["name", "address"]   # Which params are mandatory
            }
        }
    },
    # ... more tools
]
```

**Key Design Decisions:**

| Decision | Wrong Approach | Correct Approach |
|----------|---------------|-----------------|
| Building lookup | `building_id: int` (user doesn't know IDs) | `building_name: str` (look up ID internally) |
| Date handling | Pass raw string | Use `dateutil.parser` for flexible parsing |
| Duplicate check | Insert blindly | Query first, return existing if found |

#### 2c. Write the Tool Executor

The executor runs when the LLM says "call this function with these args":

```python
def execute_tool(tool_name: str, args: dict, db: Client) -> str:
    try:
        if tool_name == "add_new_building":
            name = args.get("name")
            address = args.get("address")

            # ALWAYS validate inputs first
            if not name:
                return "Missing required field: name."

            # ALWAYS check for duplicates before INSERT
            existing = db.table("buildings").select("id, name, address").ilike("name", name).execute()
            if existing.data:
                b = existing.data[0]
                return f"A building named '{b['name']}' already exists at '{b['address']}' (ID: {b['id']})."

            # Now safe to insert
            result = db.table("buildings").insert({"name": name, "address": address}).execute()
            if result.data:
                return f"Building '{name}' successfully created with ID {result.data[0]['id']}."
            return "Failed to add building."

        elif tool_name == "add_new_unit":
            # Key pattern: user gives building NAME, we look up the ID
            building_name = args.get("building_name")

            building_res = db.table("buildings").select("id, name").ilike("name", f"%{building_name}%").execute()

            if not building_res.data:
                return f"No building found with name '{building_name}'."
            if len(building_res.data) > 1:
                options = ", ".join(f"'{b['name']}'" for b in building_res.data)
                return f"Multiple matches: {options}. Please be more specific."

            building_id = building_res.data[0]["id"]
            # ... proceed with insert using building_id

        # ... other tools

    except Exception as e:
        return f"Tool execution error: {str(e)}"
```

**Why return strings?** The tool result is sent back to the LLM as a message. The LLM reads your string and formulates the final human-readable response. Never return raw Python dicts — always format as readable strings.

#### 2d. Write the Main run_chat() Function

This is the multi-turn loop that drives the conversation:

```python
def run_chat(messages: list, db: Client) -> str:
    client = Groq(api_key=settings.GROQ_API_KEY)

    # 1. Inject system prompt with today's date
    today = datetime.now().strftime("%A, %B %d, %Y")
    system_content = _SYSTEM_PROMPT_BASE.format(today=today)
    system_message = {"role": "system", "content": system_content}

    # 2. Truncate history to last 10 messages (context window management)
    truncated = messages[-10:] if len(messages) > 10 else messages
    full_messages = [system_message] + truncated

    # 3. Multi-turn loop with hard cap
    for _ in range(MAX_TOOL_CALL_TURNS):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=full_messages,
                tools=TOOLS,
                tool_choice="auto",   # LLM decides when to call a tool
            )
        except BadRequestError as e:
            if "tool_use_failed" in str(e):
                # LLM hallucinated a bad tool call — retry without tools
                fallback = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=full_messages,
                )
                return fallback.choices[0].message.content or "I couldn't process that."
            raise

        msg = response.choices[0].message

        # 4. Add assistant turn to message history
        assistant_entry = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        full_messages.append(assistant_entry)

        # 5. No tool calls = final answer
        if not msg.tool_calls:
            return msg.content or "I couldn't generate a response."

        # 6. Execute tools, add results to history, loop again
        for tool_call in msg.tool_calls:
            try:
                tool_args = json.loads(tool_call.function.arguments)
            except (json.JSONDecodeError, TypeError):
                tool_args = {}

            result = execute_tool(tool_call.function.name, tool_args, db)

            full_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,  # Must match the tool_call.id above
                "content": result,
            })

    return "I've reached the maximum number of steps. Please try rephrasing your request."
```

**The message format matters.** The Groq API requires:
1. `{"role": "system", "content": "..."}` — first
2. `{"role": "user", "content": "..."}` — user message
3. `{"role": "assistant", "content": "...", "tool_calls": [...]}` — LLM response with tool calls
4. `{"role": "tool", "tool_call_id": "...", "content": "..."}` — tool result (one per tool call)
5. `{"role": "assistant", "content": "..."}` — final answer (no tool_calls key)

### Step 3: Create the Route

**File:** `backend/app/routes/chat.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from supabase import Client
from app.db.session import get_db
from app.ai import chatbot

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]  # Only these two roles from frontend
    content: str = Field(..., max_length=10000)

class ChatRequest(BaseModel):
    messages: list[ChatMessage]

@router.post("")
async def chat_endpoint(request: ChatRequest, db: Client = Depends(get_db)):
    # Guard: reject messages over 2000 chars (prompt injection protection)
    user_messages = [m for m in request.messages if m.role == "user"]
    if user_messages and len(user_messages[-1].content) > 2000:
        raise HTTPException(status_code=400, detail="Message too long. Maximum 2000 characters.")

    try:
        messages = [m.model_dump() for m in request.messages]
        reply = chatbot.run_chat(messages, db)
        return {"reply": reply}
    except Exception as e:
        print(f"[ERROR] Chat endpoint failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Chat service error.")
```

### Step 4: Register the Router

```python
# backend/app/main.py
from app.routes import complaints, voice, ..., chat  # add chat

app.include_router(chat.router)  # add this line
```

### Step 5: Verify the Backend Works

```bash
# Start the backend
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Test with curl (Windows Git Bash)
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is todays date?"}]}'

# Expected response:
# {"reply": "Today's date is Monday, March 16, 2026."}
```

---

## 4. Part 3 — Building the AI Chatbot (Frontend)

### Step 1: Add the API Call to apiService.js

**Rule:** Every HTTP call in this project lives in `frontend/src/services/apiService.js`. No exceptions.

```javascript
// frontend/src/services/apiService.js

// ==================== CHAT API ====================

/** Send a conversation history to the AI chatbot and get the next reply. */
export async function sendChatMessage(messages) {
    const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages }),
    });
    if (!response.ok) throw new Error(`Chat error: ${response.status}`);
    return await response.json(); // { reply: string }
}
```

### Step 2: Build the Chatbot Component

**File:** `frontend/src/components/Chatbot.jsx`

Key design decisions:
- **Position:** `bottom-4 right-4` (NOT left — sidebar is on the left)
- **State:** `messages` array + `input` string + `loading` boolean
- **Animation:** Framer Motion `AnimatePresence` for smooth open/close
- **UX:** Auto-scroll to latest message; Enter key sends

```jsx
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle, X, Send } from 'lucide-react';
import { sendChatMessage } from '../services/apiService';

export default function Chatbot() {
    const [open, setOpen] = useState(false);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const bottomRef = useRef(null);

    // Auto-scroll when messages change
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    async function handleSend() {
        const text = input.trim();
        if (!text || loading) return;

        const userMsg = { role: 'user', content: text };
        const updated = [...messages, userMsg];
        setMessages(updated);
        setInput('');
        setLoading(true);

        try {
            // Pass FULL history so the LLM has conversation context
            const data = await sendChatMessage(updated);
            setMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);

            // After any chatbot action, tell the dashboard to refresh its data
            // (in case the LLM called a tool that modified the DB)
            window.dispatchEvent(new Event('refresh-appointments'));
        } catch {
            setMessages(prev => [
                ...prev,
                { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
            ]);
        } finally {
            setLoading(false);
        }
    }

    // ... JSX (see full file in codebase)
}
```

**Important pattern — cross-component refresh via custom events:**

The chatbot lives outside the main dashboard component tree. When it reschedules an appointment, the calendar needs to know. The clean way to do this without prop drilling or shared state is:

```javascript
// In Chatbot.jsx — emit the event after every successful reply
window.dispatchEvent(new Event('refresh-appointments'));

// In App.jsx — listen for the event and reload data
useEffect(() => {
    window.addEventListener('refresh-appointments', loadAppointments);
    return () => window.removeEventListener('refresh-appointments', loadAppointments);
}, []);
```

### Step 3: Add Chatbot to App.jsx

The chatbot should render OUTSIDE the main flex layout (it's `position: fixed`). This requires a React Fragment because JSX returns can only have one root element:

```jsx
// frontend/src/App.jsx

// WRONG — JSX error: "Adjacent JSX elements must be wrapped"
return (
    <div className="flex h-screen...">...</div>
    <Chatbot />   // ← can't have a sibling to root div
);

// CORRECT — wrap in a fragment
return (
    <>                           {/* Fragment has no DOM output */}
        <div className="flex h-screen...">...</div>
        <Chatbot />              {/* Renders fixed, independent of layout */}
    </>
);
```

---

## 5. Part 4 — Live Debugging Session

This section documents every bug we hit during live testing and how we solved them.

### Bug 1: Groq model decommissioned

**Symptom:**
```
groq.BadRequestError: Error code: 400 - {'error': {'message': "model_decommissioned:
The model `llama-3.1-70b-versatile` has been decommissioned..."}}
```

**Root cause:** The plan picked `llama-3.1-70b-versatile` but Groq decommissioned it after the plan was written.

**How to diagnose:** List available models:
```bash
curl -s https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $GROQ_API_KEY" | python -m json.tool | grep '"id"'
```

**Fix:** Switch to the active successor model:
```python
# chatbot.py
model="llama-3.3-70b-versatile"  # active as of March 2026
```

**Lesson:** Always check model availability at the time of implementation. Use the models list API to verify before hardcoding a model name.

---

### Bug 2: BadRequestError — tool_use_failed

**Symptom:**
```
groq.BadRequestError: Error code: 400 - {'error': {'type': 'tool_use_failed',
'message': "Tool 'brave_search' is not in the provided tools list..."}}
```

**Root cause:** `llama-3.3-70b-versatile` occasionally "hallucinates" a tool call for a tool that isn't in the tools schema (here: `brave_search`). This is an LLM reliability issue — the model was fine-tuned on data that included tools like `brave_search` and sometimes generates calls to them even when not provided.

**How to diagnose:** Catch the specific error and log the tool name being called.

**Fix:** Add a fallback handler — if the model hallucinated a bad tool call, retry without the tools schema:
```python
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=full_messages,
        tools=TOOLS,
        tool_choice="auto",
    )
except BadRequestError as e:
    if "tool_use_failed" in str(e):
        # Retry as plain text completion — no tools
        fallback = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=full_messages,
            # NOTE: no tools= argument here
        )
        return fallback.choices[0].message.content or "I'm sorry, I couldn't process that request."
    raise  # Re-raise other BadRequestErrors (e.g., bad message format)
```

**Lesson:** LLMs are probabilistic. Always handle the case where the model does something unexpected. Never let LLM errors propagate unhandled to the user.

---

### Bug 3: Chatbot doesn't know today's date

**Symptom:** User asks "What is today's date?" and the bot says "I don't have access to the current date."

**Root cause:** The system prompt was defined as a module-level constant:
```python
SYSTEM_PROMPT = "...Today's date is March 10, 2026."  # ← hardcoded at import time
```

The file is imported once when the server starts. The date never updates.

**Fix:** Make the system prompt a template and inject the date at request time:
```python
_SYSTEM_PROMPT_BASE = "...Today's date is {today}..."

def run_chat(messages, db):
    today = datetime.now().strftime("%A, %B %d, %Y")
    system_content = _SYSTEM_PROMPT_BASE.format(today=today)
```

**Lesson:** Any context that can change (time, user identity, environment) must be injected at request time, not at module import time.

---

### Bug 4: LLM reschedules the WRONG appointment

**Symptom:** User says "Reschedule appointment 99999 to tomorrow." LLM reschedules appointment 47 instead.

**Root cause:** The LLM is designed to be "helpful." When it can't find appointment 99999, it tries to be helpful by picking the first appointment it finds and rescheduling that instead. This is dangerous behavior.

**Fix:** Add an explicit rule to the system prompt:
```
- When rescheduling, use ONLY the appointment ID that the user explicitly stated.
  If that appointment is not found, tell the user it does not exist —
  do NOT substitute a different appointment ID.
```

Also, the tool executor itself enforces this:
```python
fetch = db.table("appointments").select("id, status").eq("id", appointment_id).execute()
if not fetch.data:
    return f"No appointment found with ID {appointment_id}. Please verify the appointment ID and try again."
```

**Lesson:** LLMs will hallucinate "helpful" behavior unless you explicitly prohibit it. Add explicit rules for any behavior that could be dangerous if done incorrectly.

---

### Bug 5: Adding a building creates duplicates

**Symptom:** User adds "Sunrise Towers." Page refreshes, they try to add a unit to "Sunrise Towers," and instead of finding the existing building, it creates a second "Sunrise Towers."

**Root cause:** The `add_new_building` tool had no duplicate check. It inserted blindly.

**Fix:** Check for existing building before inserting:
```python
elif tool_name == "add_new_building":
    name = args.get("name")
    address = args.get("address")

    # Check for duplicate FIRST
    existing = db.table("buildings").select("id, name, address").ilike("name", name).execute()
    if existing.data:
        b = existing.data[0]
        return (
            f"A building named '{b['name']}' already exists at '{b['address']}' "
            f"(ID: {b['id']}). Use this building to add units."
        )

    # Only insert if truly new
    result = db.table("buildings").insert({"name": name, "address": address}).execute()
```

**Testing this fix in isolation:**
```python
# You can test tool functions directly in a Python shell without the LLM
import sys; sys.path.insert(0, 'backend')
from app.db.session import get_db
from app.ai.chatbot import execute_tool

db = next(get_db())
result = execute_tool('add_new_building', {'name': 'Sunrise Towers', 'address': '123 Main St'}, db)
print(result)  # Should say "already exists (ID: ...)"
```

---

### Bug 6: Rescheduled appointments don't appear on calendar

**This was actually TWO bugs stacked:**

**Sub-bug A: Calendar doesn't refresh after chatbot action**

The chatbot and the calendar are separate components. When the chatbot reschedules an appointment via the LLM, the calendar's React state is stale. We need to tell it to reload.

Fix: Dispatch a custom browser event after every chatbot reply:
```javascript
// Chatbot.jsx
window.dispatchEvent(new Event('refresh-appointments'));

// App.jsx
window.addEventListener('refresh-appointments', loadAppointments);
```

**Sub-bug B: Date format incompatibility — space vs T separator**

The calendar uses `date-fns`'s `parseISO()` function. This function requires ISO 8601 format with a `T` separator:
```
parseISO("2026-03-16T14:30:00")  // ✅ works
parseISO("2026-03-16 14:30:00")  // ❌ returns Invalid Date
```

But the original `reschedule_appointment` tool was storing dates with a space:
```python
normalized_date = parsed.strftime("%Y-%m-%d %H:%M:%S")  # ❌ space separator
```

Fix: Use `T` separator when storing dates:
```python
normalized_date = parsed.strftime("%Y-%m-%dT%H:%M:%S")  # ✅ T separator
```

**Lesson:** Date format consistency is critical. Establish one canonical format for your project (ISO 8601 with T) and enforce it everywhere: DB reads, DB writes, API responses, and frontend parsing.

---

## 6. Part 5 — VAPI Webhook Design

VAPI is a voice AI platform that calls your backend endpoints during a phone conversation. VAPI endpoint design has very specific requirements that differ from normal REST API design.

### The Core Contract for VAPI Endpoints

VAPI calls your endpoints **mid-conversation**. If your endpoint returns a 404 or 500, VAPI's AI doesn't know how to handle it and the conversation breaks or hangs.

**Rule 1: VAPI endpoints should always return HTTP 200.**

```python
# WRONG for VAPI — 404 breaks the conversation
if not flat_response.data:
    raise HTTPException(status_code=404, detail="Flat not found")

# CORRECT for VAPI — return 200 with a boolean field
if not flat_response.data:
    return JSONResponse(status_code=200, content={"exists": False})
```

**Rule 2: Use a boolean `exists` field for branching logic.**

VAPI reads your response and uses variables like `exists` to decide what to say. Structure your response so the AI can make a binary decision:
```json
{ "exists": true, "tenant_name": "John Smith", "tenant_phone": "+447700000000" }
{ "exists": false }
```

**Rule 3: Never leak stack traces to VAPI.**

```python
except Exception as e:
    print(f"Error: {str(e)}")  # Log internally
    return JSONResponse(status_code=200, content={"exists": False})  # Safe default to caller
```

**Rule 4: Normalize inputs.**

Callers say things like "flat A dash five one two" → VAPI transcribes it as "A-512" or "a-512" or "A512". Always normalize:
```python
normalized = flat_number.strip().upper()  # "a-512 " → "A-512"
```

### Pattern: POST /flats/verify (Flat Verification)

This endpoint is called by VAPI at the start of a conversation to verify the caller's flat exists and get tenant details.

**Old pattern (path parameter):**
```
GET /tenants/by-flat/{flat_no}
```
Problem: Path parameter in URL means the flat number must be URL-encoded. Special characters like `/` or `#` in flat numbers can break routing.

**New pattern (request body):**
```
POST /flats/verify
Body: {"flat_number": "A-512"}
```

```python
# backend/app/routes/flats.py

class FlatVerifyRequest(BaseModel):
    flat_number: str

class FlatVerifyResponse(BaseModel):
    exists: bool
    tenant_name: Optional[str] = None
    tenant_number: Optional[str] = None
    datetime: Optional[str] = None  # Current time for AI awareness

@router.post("/verify", response_model=FlatVerifyResponse)
async def verify_flat(request: FlatVerifyRequest, db: Client = Depends(get_db)):
    try:
        # Always normalize before DB query
        normalized = request.flat_number.strip().upper()

        response = db.table("flats").select("*").ilike("flat_number", normalized).execute()

        if not response.data:
            return FlatVerifyResponse(exists=False)

        flat = response.data[0]

        # Get tenant if flat has one
        tenant_name = None
        tenant_number = None
        if flat.get("tenant_uuid"):
            t = db.table("tenants").select("name, phone").eq("uuid", flat["tenant_uuid"]).execute()
            if t.data:
                tenant_name = t.data[0].get("name")
                tenant_number = t.data[0].get("phone")

        # Return current time so VAPI's AI knows the datetime context
        current_time = datetime.now(IST).strftime("%Y-%m-%dT%H:%M:%S")

        return FlatVerifyResponse(
            exists=True,
            tenant_name=tenant_name,
            tenant_number=tenant_number,
            datetime=current_time
        )
    except Exception as e:
        print(f"Error verifying flat: {e}")
        return FlatVerifyResponse(exists=False)  # Safe default, never 500
```

### Pattern: Migrating Away from /tenants/by-flat/{flat_no}

The old `GET /tenants/by-flat/{flat_no}` endpoint had problems:

1. **Responsibility mismatch:** Looking up a flat should be a `flats` concern, not a `tenants` concern.
2. **Path parameter routing issues:** Flat numbers with special chars can conflict with FastAPI's router.
3. **Redundant endpoint:** `/flats/verify` does the same thing better.

When removing old VAPI endpoints, follow this checklist:
1. Check if any VAPI assistant configuration references the old URL
2. Update VAPI dashboard to point to the new endpoint
3. Test the new endpoint with curl first
4. Remove the old route file code
5. Deploy and monitor for errors

### Pattern: GET /appointments/availability

This endpoint lets VAPI check if a time slot is available before booking:

```python
@router.get("/availability")
async def get_appointment_availability(
    flat_number: str = Query(...),
    date: str = Query(..., description="YYYY-MM-DD"),
    db: Client = Depends(get_db)
):
    """
    VAPI tool — Check if a flat has any appointments on a given date.
    Always returns 200. Uses boolean 'available' field for AI logic.
    """
    try:
        normalized = flat_number.strip().upper()
        start = f"{date} 00:00:00"
        end = f"{date} 23:59:59"

        existing = (
            db.table("appointments")
            .select("id, appointment_date, status")
            .ilike("flat_number", normalized)
            .gte("appointment_date", start)
            .lte("appointment_date", end)
            .neq("status", "cancelled")  # Cancelled slots are available
            .execute()
        )

        if existing.data:
            return {
                "available": False,
                "reason": f"Flat {normalized} already has an appointment on {date}.",
                "existing_appointments": [
                    {"id": a["id"], "time": a["appointment_date"], "status": a["status"]}
                    for a in existing.data
                ]
            }

        return {"available": True}

    except Exception as e:
        print(f"Error checking availability: {e}")
        return {"available": False, "reason": "Could not check availability."}
```

### VAPI Endpoint Checklist

Before deploying a VAPI endpoint, verify:
- [ ] Returns HTTP 200 on all paths (including errors)
- [ ] Has a boolean field (`exists`, `available`, `success`) for AI branching
- [ ] Normalizes string inputs (strip + upper for flat numbers)
- [ ] Has `try/except` that returns a safe default, not a 500
- [ ] Returns datetime context if the AI needs time awareness
- [ ] Tested with curl before connecting to VAPI dashboard

---

## 7. Commands Reference

### Starting the Development Environment

```bash
# Backend (in Git Bash or terminal 1)
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (in Git Bash or terminal 2)
cd frontend
npm run dev
# → http://localhost:5173
```

### Testing Backend Endpoints with curl

```bash
# Test chatbot — single message
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is todays date?"}]}'

# Test chatbot — multi-turn conversation
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Add a building called Test Tower at 1 Main St"},
      {"role": "assistant", "content": "Are you sure you want to add Test Tower?"},
      {"role": "user", "content": "Yes, go ahead"}
    ]
  }'

# Test flat verification
curl -s -X POST http://127.0.0.1:8000/flats/verify \
  -H "Content-Type: application/json" \
  -d '{"flat_number": "A-101"}'

# Test appointment check
curl -s "http://127.0.0.1:8000/appointments?start_date=2026-03-16&end_date=2026-03-16"

# Test Groq available models (to find active models)
curl -s https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $GROQ_API_KEY" | python -m json.tool

# Check API docs (FastAPI generates these automatically)
# Open in browser: http://127.0.0.1:8000/docs
```

### Testing Tool Functions Directly in Python

```bash
# Open Python shell in project root
cd backend
python

# Inside Python:
import sys
sys.path.insert(0, '.')
from app.db.session import get_db
from app.ai.chatbot import execute_tool

db = next(get_db())

# Test add_new_building
result = execute_tool('add_new_building', {'name': 'Sunrise Towers', 'address': '123 Main St'}, db)
print(result)

# Test add_new_unit with building name lookup
result = execute_tool('add_new_unit', {
    'flat_number': 'ST-101',
    'address': '123 Main St',
    'building_name': 'Sunrise Towers'
}, db)
print(result)

# Test reschedule with non-existent ID
result = execute_tool('reschedule_appointment', {
    'appointment_id': 99999,
    'new_date': '2026-03-20 10:00:00'
}, db)
print(result)  # Should say "No appointment found with ID 99999"
```

### Git Workflow

```bash
# Check what changed
git status
git diff

# Stage specific files (not git add -A — that catches .env files)
git add backend/app/ai/chatbot.py
git add backend/app/routes/chat.py
git add frontend/src/components/Chatbot.jsx

# Commit
git commit -m "feat: implement AI chatbot with Groq tool calling"

# View recent commits
git log --oneline -10
```

---

## 8. Industry Best Practices Applied

### 1. Audit Before Implementation
Always review a plan against the actual codebase before writing a single line of code. A 30-minute audit saved hours of rework.

### 2. Follow Existing Conventions
When adding a new feature, look at how existing features are structured:
- Where does the route go? (`routes/`)
- What prefix does it use? (check `main.py`)
- Where does the API call go? (`apiService.js`)
- How is DB access done? (Dependency injection via `Depends(get_db)`)

Never deviate from project conventions without a strong reason.

### 3. Separate Concerns
- **chatbot.py:** Business logic only (no HTTP, no FastAPI)
- **routes/chat.py:** HTTP handling only (validation, dependency injection)
- **apiService.js:** All HTTP calls (never inline fetch in components)
- **Chatbot.jsx:** UI only (no business logic)

### 4. Context Window Management
LLMs have finite context windows. Always truncate long conversations before sending:
```python
truncated = messages[-10:] if len(messages) > 10 else messages
```

### 5. Graceful Degradation
When an LLM does something unexpected (`tool_use_failed`), don't crash. Fall back gracefully:
```python
except BadRequestError as e:
    if "tool_use_failed" in str(e):
        # Retry as plain text — less capable but at least something
        fallback = client.chat.completions.create(model=MODEL, messages=full_messages)
        return fallback.choices[0].message.content
```

### 6. Always Check for Duplicates Before INSERT
```python
# Pattern: check → insert
existing = db.table("buildings").select("id").ilike("name", name).execute()
if existing.data:
    return f"Already exists: {existing.data[0]['id']}"
result = db.table("buildings").insert({...}).execute()
```

### 7. Validate Inputs at System Boundaries
Validate at the API boundary (Pydantic schemas), not deep inside business logic:
```python
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]   # Enum validation
    content: str = Field(..., max_length=10000)  # Length validation
```

### 8. Dynamic Context Injection
Never hardcode time-sensitive information at module level. Inject at request time:
```python
today = datetime.now().strftime("%A, %B %d, %Y")
prompt = BASE_PROMPT.format(today=today)
```

### 9. Use .ilike() for User Input String Matching
When matching user-supplied strings against DB values, use case-insensitive matching:
```python
db.table("buildings").select("*").ilike("name", f"%{user_input}%")
# NOT: .eq("name", user_input)  ← case sensitive, breaks on "sunrise" vs "Sunrise"
```

### 10. Cross-Component Communication with Custom Events
For loosely coupled components that need to stay in sync, use browser custom events:
```javascript
window.dispatchEvent(new Event('refresh-appointments'))  // sender
window.addEventListener('refresh-appointments', callback)  // receiver
```

---

## 9. Resources and Further Reading

### Groq API
- **Groq Console (get API keys):** https://console.groq.com/keys
- **Groq Python SDK docs:** https://console.groq.com/docs/openai
- **Tool calling docs:** https://console.groq.com/docs/tool-use
- **Available models list:** https://console.groq.com/docs/models
- **Rate limits:** https://console.groq.com/docs/rate-limits

### LLM Tool Calling Pattern
- **OpenAI Function Calling Guide** (same format, Groq is compatible): https://platform.openai.com/docs/guides/function-calling
- **Langchain Tool Calling Blog** (good conceptual explanation): https://blog.langchain.dev/tool-calling-with-langchain/
- **JSON Schema Reference** (for writing tool parameter schemas): https://json-schema.org/understanding-json-schema/

### FastAPI
- **FastAPI Official Docs:** https://fastapi.tiangolo.com/
- **Dependency Injection in FastAPI:** https://fastapi.tiangolo.com/tutorial/dependencies/
- **Pydantic V2 docs (validation):** https://docs.pydantic.dev/latest/
- **Path vs Query Parameters:** https://fastapi.tiangolo.com/tutorial/path-params/

### Supabase Python SDK
- **Supabase Python docs:** https://supabase.com/docs/reference/python/introduction
- **Filtering (ilike, eq, gte):** https://supabase.com/docs/reference/python/using-filters

### React + Frontend
- **Framer Motion docs (animations):** https://www.framer.com/motion/
- **Lucide React icons:** https://lucide.dev/icons/
- **Custom Events API (MDN):** https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/dispatchEvent
- **useRef for scroll:** https://react.dev/reference/react/useRef

### VAPI Integration
- **VAPI Docs:** https://docs.vapi.ai/
- **VAPI Server URL (webhook) pattern:** https://docs.vapi.ai/server-url
- **VAPI Tool Functions:** https://docs.vapi.ai/tools/function

### General Best Practices
- **OWASP Top 10 (security):** https://owasp.org/www-project-top-ten/
- **REST API Design Best Practices:** https://www.freecodecamp.org/news/rest-api-best-practices-rest-endpoint-design-examples/
- **Feature Flags / Phased Rollout (for production):** https://martinfowler.com/articles/feature-toggles.html

### LLM Prompt Engineering
- **OpenAI Prompt Engineering Guide:** https://platform.openai.com/docs/guides/prompt-engineering
- **System Prompt Best Practices:** https://www.promptingguide.ai/techniques/system-prompt
- **Prompt Injection (security risk):** https://simonwillison.net/2023/Apr/14/prompt-injection/

---

## Quick Reference: Common Mistakes and Fixes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Hardcoded date in system prompt | Bot always says wrong date | Use `{today}` placeholder, inject in `run_chat()` |
| Space in stored datetime | Calendar shows wrong dates | Use `%Y-%m-%dT%H:%M:%S` (with T) |
| No duplicate check before INSERT | Double buildings/units | `ilike("name", name)` check first |
| Building_id in tool schema | LLM asks user for ID | Use `building_name`, look up ID internally |
| Infinite tool call loop | Server hangs | Add `MAX_TOOL_CALL_TURNS = 5` hard cap |
| No fallback for tool_use_failed | 400 error crashes chat | Catch `BadRequestError`, retry without tools |
| FAB at bottom-left | Hidden behind sidebar | Use `bottom-4 right-4` |
| Inline fetch in component | Inconsistent error handling | Move to `apiService.js` |
| No `refresh-appointments` event | Calendar doesn't update | Dispatch event after every chatbot reply |
| Adjacent JSX elements | Build error | Wrap in `<>...</>` fragment |

---

*Guide written after Session 16 — March 16, 2026*

---

# Session 17 — Switching LLM Providers, Expanding Chatbot Capabilities, and Debugging Silent Failures

> **What changed this session:** We migrated the chatbot from Groq → OpenAI, added a full property-management tool suite (properties → buildings → units), and fixed three classes of bugs that caused the LLM to silently lie to the user.

---

## Table of Contents (Session 17)

1. [Migrating from Groq to OpenAI](#s17-1-migrating-from-groq-to-openai)
2. [Expanding the Tool Suite — Full Property Hierarchy](#s17-2-expanding-the-tool-suite)
3. [Bug 7 — LLM Claims Success When No Tool Exists](#s17-bug7)
4. [Bug 8 — `required` Fields Silently Block Tool Calls](#s17-bug8)
5. [Bug 9 — Duplicate Buildings Block Unit Creation](#s17-bug9)
6. [The Golden Rule for Tool Schema Design](#s17-golden-rule)
7. [Updated Quick Reference](#s17-quick-reference)
8. [OpenAI Resources](#s17-resources)

---

## S17-1: Migrating from Groq to OpenAI

### Why switch?

LLM providers offer the same OpenAI-compatible API format but differ in:
- Model quality and reliability
- Tool calling behaviour (Groq's `llama` models hallucinate tool names; GPT-4o-mini does not)
- Cost and rate limits
- API key management

The project switched because the Groq `llama-3.3-70b-versatile` model was unreliable with tool calling (see Bug 2 in Session 16). OpenAI's `gpt-4o-mini` is faster, cheaper, and does not hallucinate tool names.

### Step-by-step migration

**1. Add the new key to `.env`:**
```bash
# .env
OPEN_AI_API=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Get your key at: https://platform.openai.com/api-keys

**2. Register it in `config.py`:**
```python
class Settings:
    OPEN_AI_API: str = os.getenv("OPEN_AI_API", "")
    # Remove: GROQ_API_KEY
```

**3. Swap the client in `chatbot.py`:**
```python
# Before (Groq)
from groq import Groq, BadRequestError
client = Groq(api_key=settings.GROQ_API_KEY)

# After (OpenAI)
from openai import OpenAI, BadRequestError
client = OpenAI(api_key=settings.OPEN_AI_API)
```

**4. Change the model name:**
```python
# Before
model="llama-3.3-70b-versatile"

# After
model="gpt-4o-mini"
```

**5. Update `requirements.txt`:**
```diff
- groq==1.0.0
+ openai>=1.0.0
```

**6. Install the new package:**
```bash
pip install openai
```

### How to verify the API key is working BEFORE touching the chatbot

Always test a new API key in isolation — a single Python one-liner. This tells you immediately if the key is valid, the model name is correct, and the network can reach the API. Don't run the full server just to check the key.

```bash
cd backend
python -c "
from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()
client = OpenAI(api_key=os.getenv('OPEN_AI_API'))
resp = client.chat.completions.create(
    model='gpt-4o-mini',
    messages=[{'role': 'user', 'content': 'Say OK'}],
    max_tokens=5
)
print('API key works:', resp.choices[0].message.content)
"
```

**Expected output:**
```
API key works: OK!
```

**If it fails**, the error message tells you exactly what's wrong:
- `AuthenticationError` → bad key
- `NotFoundError` → wrong model name
- `ConnectionError` → network issue / wrong base URL

**Senior dev intuition:** Test every external dependency independently before integrating it. This takes 30 seconds and saves hours of chasing bugs caused by a bad key.

---

## S17-2: Expanding the Tool Suite

### The property hierarchy

The data model has 3 levels:
```
properties_list  (top-level "properties")
    └── buildings        (buildings inside a property)
            └── flats    (units/flats inside a building)
```

Each level needs: **list**, **create**, and **delete** tools. We also need **link** support — when creating a building, optionally link it to a property by name.

### Complete tool list after Session 17

| Tool | Required params | Optional params | Notes |
|------|----------------|-----------------|-------|
| `list_properties` | — | `name_filter` | Returns ID, name, address |
| `add_new_property` | `name` | `address`, `description` | Duplicate check by name |
| `delete_property` | `property_id` | — | Blocked if buildings exist |
| `list_buildings` | — | `name_filter` | Returns ID, name, address |
| `add_new_building` | `name` | `address`, `property_name` | Links to property by name |
| `delete_building` | `building_id` | — | Blocked if units exist |
| `add_new_unit` | `flat_number`, `building_name` | `address` | Links to building by name |
| `delete_unit` | `flat_number` | — | Blocked if occupied |
| `get_tenant_details` | — | `tenant_name`, `phone_number` | At least one required |
| `check_appointments_by_date` | `date` | — | Returns all appts for that day |
| `reschedule_appointment` | `appointment_id`, `new_date` | — | Validates ID exists first |

### Key design decisions

**1. Look up by name, not by ID.**

Users naturally say "add a building to Sunrise Property." They don't say "add a building to property_id=abc123." All tools that reference a parent entity accept a name and look up the ID internally:

```python
# Tool schema: property_name (string, human-readable)
# Handler: look up property_id from DB

prop_res = db.table("properties_list")
    .select("id, name")
    .ilike("name", f"%{property_name}%")
    .execute()
payload["property_id"] = prop_res.data[0].get("id")
```

**2. Safety checks before every DELETE.**

A building with units cannot be deleted. A unit with a tenant cannot be deleted. This prevents cascading data loss and gives the user a clear message about what to fix first:

```python
elif tool_name == "delete_building":
    flats_check = db.table("flats").select("id").eq("building_id", building_id).execute()
    if flats_check.data:
        return (
            f"Cannot delete building — it has {len(flats_check.data)} unit(s). "
            f"Remove all units first."
        )
    db.table("buildings").delete().eq("id", building_id).execute()
    return f"Building deleted."
```

**3. Duplicate checks before every INSERT.**

```python
existing = db.table("properties_list").select("id").ilike("name", name).execute()
if existing.data:
    return f"A property named '{name}' already exists (ID: {existing.data[0]['id']})."
```

**4. Update the system prompt when tools change.**

The first line of the system prompt describes what the bot can do. Update it every time you add or remove tools — the LLM uses this to understand its own capabilities:

```python
_SYSTEM_PROMPT_BASE = """You are a property management assistant.
You can add/delete properties, add/delete buildings (and link them to properties),
add/delete units, retrieve tenant information, and check or reschedule appointments.
```

### Testing a new tool without the LLM

Every tool in `execute_tool()` is just a Python function. You can test it directly in a shell without starting the server or involving the LLM at all:

```bash
cd backend
python -c "
import sys
sys.path.insert(0, '.')
from app.db.session import get_db
from app.ai.chatbot import execute_tool

db = next(get_db())

# Test list_properties
print(execute_tool('list_properties', {}, db))

# Test add_new_property
print(execute_tool('add_new_property', {'name': 'Test Property'}, db))

# Test delete_property (use the ID from the output above)
# print(execute_tool('delete_property', {'property_id': 'paste-id-here'}, db))
"
```

**Why this matters:** If the tool logic is broken, this tells you immediately. You don't waste time wondering whether the bug is in the LLM, the route, or the tool itself. Always isolate the layer.

---

<a name="s17-bug7"></a>
## Bug 7 — LLM Claims Success When No Tool Exists

**Symptom:** User asks: *"Remove the duplicate buildings and add unit T33 to Test Tower."* The chatbot replies: *"Done! I've removed the duplicates and added unit T33."* But when you check the DB — nothing changed.

**Root cause:** The chatbot had no `delete_building` tool. When the LLM received a request to delete buildings, it had no tool to call. Instead of saying *"I can't do that,"* it simply lied and said the action was complete.

This is the **hallucinated success** failure mode. It is one of the most dangerous LLM bugs because:
- The user believes the action happened
- The actual state is unchanged
- There is no error — HTTP 200, no exception

**How to diagnose:**

Check the server logs. Every tool call goes through the backend. If the action actually happened, you'll see the DB call in the logs. If you see only `POST /chat 200 OK` and nothing else — no `GET /buildings`, no `DELETE /buildings/...` — the tool was never called.

```
# Logs when tool IS called (real action):
INFO: POST /chat HTTP/1.1" 200 OK
# ... followed by DB operations inside execute_tool

# Logs when tool is NOT called (LLM hallucinated):
INFO: POST /chat HTTP/1.1" 200 OK
# ... nothing else. The LLM just made up a response.
```

**Fix part 1: Add the missing tool.**

If the user needs to be able to do something, there must be a corresponding tool. No tool = no action = LLM will lie.

```python
# Added in chatbot.py:
elif tool_name == "delete_building":
    building_id = args.get("building_id")
    # ... safety check, then delete
    db.table("buildings").delete().eq("id", building_id).execute()
    return f"Building deleted."
```

**Fix part 2: Add CRITICAL rules to the system prompt.**

Even with the tool added, reinforce the rule explicitly in the system prompt:

```python
_SYSTEM_PROMPT_BASE = """...
- CRITICAL: Never claim an action was completed unless you received a success result
  from the tool. If a tool returns an error or is unavailable, tell the user exactly
  what happened.
- CRITICAL: You can ONLY perform actions that have a corresponding tool. If the user
  asks for something you have no tool for, say so clearly — do NOT pretend the action succeeded.
"""
```

**Why the word "CRITICAL"?** Instruction-tuned models like GPT-4o-mini weight uppercase emphasis differently from normal text. Using "CRITICAL:" acts as a priority marker. It's not magic — it's a widely used prompt engineering technique to make certain rules stick over others.

**Lesson:** For every user-facing action, ask: *"Does a tool exist for this?"* If not, either add the tool or explicitly tell the LLM it cannot do it. Never assume the LLM will self-report its limitations.

---

<a name="s17-bug8"></a>
## Bug 8 — `required` Fields in Tool Schema Silently Block Tool Calls

**Symptom:** User says: *"Add a building called Tower B to Sunrise Property."* Chatbot replies: *"Tower B has been added to Sunrise Property."* But nothing is in the DB.

**Root cause:** The `add_new_building` tool had `address` in its `required` array:

```json
"required": ["name", "address"]
```

The user didn't provide an address. The LLM could not call the tool because a required parameter was missing. But instead of asking the user for the address, the LLM chose to claim success without calling the tool at all.

**Why doesn't the LLM just ask for the address?**

It might, sometimes. But GPT-4o-mini has been trained to be "helpful" and non-interrupting. When it sees a required parameter is missing, its behaviour is inconsistent — it might ask, or it might hallucinate a value, or it might just skip the call and claim success.

**How to diagnose:**

```bash
# Run a quick test in Python to verify which params are actually required
cd backend
python -c "
from app.ai.chatbot import TOOLS
for t in TOOLS:
    fn = t['function']
    print(fn['name'], '->', fn['parameters']['required'])
"
```

**Output before fix:**
```
add_new_unit -> ['flat_number', 'address', 'building_name']
add_new_building -> ['name', 'address']
...
```

**Output after fix:**
```
add_new_unit -> ['flat_number', 'building_name']
add_new_building -> ['name']
...
```

**The fix:**

Check your actual database schema. In this project, `address` is `Optional[str] = None` in every model — it was never actually required. Only mark a parameter as `required` if the DB genuinely rejects a NULL value for it.

```python
# Tool schema — WRONG
"required": ["name", "address"]   # address is NOT required in the DB

# Tool schema — CORRECT
"required": ["name"]              # only name is truly required
```

Also remove the runtime guard in the handler:
```python
# WRONG — blocks legitimate calls with no address
if not address:
    return "Missing required field: address."

# CORRECT — address is optional, only include if provided
payload = {"name": name}
if address:
    payload["address"] = address
```

**Golden rule:** The `required` array in a tool schema must match the database's NOT NULL constraints — nothing more, nothing less. If the DB accepts NULL, the tool should accept the parameter as optional.

**Lesson:** Every field in `required` is a potential blocker. If the user doesn't provide it, the LLM may silently skip the tool call. Keep `required` as minimal as possible — only the fields the DB cannot survive without.

---

<a name="s17-bug9"></a>
## Bug 9 — Duplicate Buildings Cause `add_new_unit` to Silently Fail

**Symptom:** User adds a building "Test Tower." It gets created. They try to add unit T33 to "Test Tower." The chatbot says it succeeded but T33 never appears.

**Root cause:** There were multiple rows named "Test Tower" in the `buildings` table (created from a previous hallucinated-success bug). The `add_new_unit` handler uses `ilike` to look up the building by name. When multiple matches are found, it returns an error to the LLM:

```python
if len(building_res.data) > 1:
    options = ", ".join(...)
    return f"Multiple buildings match '{building_name}': {options}."
```

The LLM received this error message but — instead of relaying it to the user — interpreted it ambiguously and claimed success anyway.

**How to diagnose:**

**Step 1:** Directly query the DB for duplicates:
```bash
cd backend
python -c "
import sys; sys.path.insert(0, '.')
from app.db.session import get_db
db = next(get_db())
res = db.table('buildings').select('id, name, address').ilike('name', '%Test Tower%').execute()
for b in res.data:
    print(b)
"
```

If you see multiple rows with the same name — you have duplicates.

**Step 2:** Check what the tool actually returns by calling it directly:
```bash
python -c "
import sys; sys.path.insert(0, '.')
from app.db.session import get_db
from app.ai.chatbot import execute_tool
db = next(get_db())
result = execute_tool('add_new_unit', {'flat_number': 'T33', 'building_name': 'Test Tower'}, db)
print(repr(result))
"
```

If the output is `"Multiple buildings match 'Test Tower': ..."` — the unit was never inserted. The problem is the duplicates.

**Fix:**

**Part 1:** Add `list_buildings` and `delete_building` tools (so the LLM can actually resolve duplicates):
```python
# In the chatbot, the user can now say:
# "Show all buildings with 'Test' in the name"
# → list_buildings returns IDs
# "Delete building with ID [duplicate-id]"
# → delete_building removes the duplicate
```

**Part 2:** The `add_new_building` handler now checks for duplicates before inserting, so new duplicates can't be created:
```python
existing = db.table("buildings").select("id").ilike("name", name).execute()
if existing.data:
    return f"Building '{name}' already exists (ID: {existing.data[0]['id']}). Use this one."
```

**To fix existing duplicates via chatbot:**
1. Ask: *"List all buildings with 'Test' in the name"*
2. Bot shows both Test Tower entries with their IDs
3. Ask: *"Delete building with ID [the-duplicate-id]"*
4. Bot confirms deletion
5. Now add the unit — only one "Test Tower" exists, lookup succeeds

**Lesson:** When a tool's lookup returns an error (multiple matches, not found, etc.), the LLM may or may not relay that error to the user. Never rely on the LLM to surface tool errors — add the `delete`/`list` tools so the user can resolve conflicts themselves.

---

<a name="s17-golden-rule"></a>
## The Golden Rule for Tool Schema Design

After these bugs, here is the complete mental checklist for every tool you write:

```
TOOL SCHEMA CHECKLIST
─────────────────────
□ name       — matches exactly what the handler checks for in execute_tool()
□ description — clear enough for the LLM to know when to call it
□ required   — ONLY fields that are NOT NULL in the DB schema
□ optional   — everything else (address, description, etc.)

TOOL HANDLER CHECKLIST
──────────────────────
□ Validate required params are present (return clear error if missing)
□ Duplicate check BEFORE any INSERT
□ Existence check BEFORE any UPDATE or DELETE
□ Safety check BEFORE DELETE (no children? not occupied?)
□ Return a clear success string — the LLM reads this to formulate its reply
□ Return a clear error string — the LLM reads this too

SYSTEM PROMPT CHECKLIST
───────────────────────
□ Describe all capabilities (update when tools change)
□ CRITICAL rule: never claim success without tool confirmation
□ CRITICAL rule: only perform actions that have a tool
□ Confirmation rule: ask user before any write/delete
```

**The information flow:**

```
User message
    ↓
LLM reads system prompt + tool schemas
LLM decides which tool to call (or none)
    ↓ (if tool called)
execute_tool() runs real DB logic
Returns a string result to LLM
    ↓
LLM reads the result string
LLM formulates a human response
    ↓
User sees the response
```

**Key insight:** The LLM never touches the DB. It only reads the string you return from `execute_tool()`. If that string says "Success", the LLM will say "Done." If it says "Error: duplicate found", the LLM should say "I couldn't do that because...". Your job as a developer is to make those strings crystal clear.

---

<a name="s17-quick-reference"></a>
## Updated Quick Reference Table

| Mistake | Symptom | Fix |
|---------|---------|-----|
| No tool for a user action | LLM claims success, nothing happens | Add the missing tool |
| `address` in `required` | LLM skips tool call, claims success | Remove from `required`; make optional in handler |
| No duplicate check before INSERT | Multiple rows with same name | Check with `ilike` before every `insert()` |
| No delete tool | LLM lies about deleting | Add `delete_X` tool with safety checks |
| No list tool | LLM can't resolve "which one?" | Add `list_X` tool to show IDs |
| System prompt outdated | LLM unaware of new tools | Update first line of system prompt when tools change |
| Delete without child-check | Orphaned records in DB | Check for children (units, buildings) before delete |
| Delete occupied unit | Tenant data loss | Check `occupied` and `tenant_uuid` before delete |
| Hardcoded API key in code | Security breach if pushed to git | Use `.env` + `os.getenv()` always |
| API key tested after integration | Hard to know which layer broke | Test key in isolation with one-liner Python first |

---

<a name="s17-resources"></a>
## OpenAI Resources

### OpenAI API
- **Get API keys:** https://platform.openai.com/api-keys
- **OpenAI Python SDK docs:** https://platform.openai.com/docs/libraries/python-library
- **Chat Completions API:** https://platform.openai.com/docs/api-reference/chat
- **Tool/Function Calling Guide:** https://platform.openai.com/docs/guides/function-calling
- **Model list (names, pricing):** https://platform.openai.com/docs/models
- **Prompt engineering guide:** https://platform.openai.com/docs/guides/prompt-engineering
- **Error codes reference:** https://platform.openai.com/docs/guides/error-codes

### Choosing a model
| Model | Use when |
|-------|----------|
| `gpt-4o` | Maximum capability — complex reasoning, production critical |
| `gpt-4o-mini` | Fast, cheap, good tool calling — **use this for most features** |
| `gpt-4-turbo` | Legacy; prefer gpt-4o |
| `gpt-3.5-turbo` | Cheapest; poor tool calling reliability |

**For this project:** `gpt-4o-mini` is the right default. It handles tool calling reliably and costs ~10x less than `gpt-4o`.

### Groq → OpenAI compatibility note
Groq's API is OpenAI-compatible (same request/response format, same tool calling schema). Migrating between them is almost entirely a matter of changing the client import, the API key, and the model name. The TOOLS schema definition is identical.

---

*Session 17 additions — March 17, 2026*

---

## Continuing Your Learning

This file covers chatbot architecture, VAPI design, LLM debugging, and tool schema best practices.

**`LEARNING_GUIDE_SESSION_17.md`** covers everything built after this session, and also contains a permanent reference section (Sections 12–19) with material that applies to all work on this project:

- **Section 12:** The complete data model (every table, every column, all relationships)
- **Section 13:** FastAPI and Pydantic V2 patterns — `Depends(get_db)`, `model_dump`, `BackgroundTasks`
- **Section 14:** Supabase SDK query patterns — `select`, `eq`, `ilike`, joins, `.maybe_single()`
- **Section 15:** React architecture — component tree, state management, view-routing, `useMemo`, `useRef`
- **Section 16:** Date and time handling — the T-separator rule, IST, `parseISO`, `dateutil`
- **Section 17:** End-to-end request traces — following a click all the way to SMS delivery
- **Section 18:** Debugging playbook — systematic approach for every error type
- **Section 19:** UUID vs integer ID — why both exist and when to use each

If you're building or debugging anything in this project and you're not sure how a layer works, Session 17's reference sections are where to look first.

# Vapi Tool Configuration - Submit Complaint with Appointment

## Updated Configuration for submit_complaint Tool

Use this configuration in your Vapi dashboard:

```json
{
  "type": "function",
  "function": {
    "name": "submit_complaint",
    "description": "Submit a complaint after collecting flat number, category, description, and preferred appointment date/time from the caller",
    "parameters": {
      "type": "object",
      "required": ["flat_number", "category", "description", "appointment_datetime"],
      "properties": {
        "flat_number": {
          "type": "string",
          "description": "The flat/apartment number (e.g., '101', 'A-205')"
        },
        "category": {
          "type": "string",
          "enum": ["plumbing", "electrical", "maintenance", "cleaning", "pest_control", "other"],
          "description": "Type of complaint"
        },
        "description": {
          "type": "string",
          "description": "Detailed description of the issue"
        },
        "appointment_datetime": {
          "type": "string",
          "description": "ISO 8601 datetime for when the manager should visit (e.g., '2026-02-10T15:00:00' for Feb 10 at 3 PM)"
        }
      }
    }
  }
}
```

## Key Changes from Previous Version

### ❌ OLD (Priority-based)
```json
{
  "flat_number": "101",
  "category": "plumbing",
  "description": "Sink leaking",
  "priority": "high"  ← Removed
}
```

### ✅ NEW (Appointment-based)
```json
{
  "flat_number": "101",
  "category": "plumbing",
  "description": "Sink leaking",
  "appointment_datetime": "2026-02-10T15:00:00"  ← Added
}
```

## Updated System Prompt

```
You are a helpful property management assistant for a residential complex.

CONVERSATION FLOW:
1. Greet: "Hello! I'm here to help with maintenance issues. What's your flat number?"
2. [Call lookup_tenant tool to verify tenant]
3. If found: "Hi {tenant_name}! What maintenance issue can I help you with?"
4. Listen and identify category (plumbing, electrical, maintenance, cleaning, pest control, or other)
5. Ask: "Can you describe the issue in detail?"
6. Ask: "When would you like the manager to visit? Please provide a date and time."
7. [Extract appointment_datetime from their response - convert to ISO format]
8. [Call submit_complaint tool with all 4 required fields]
9. Confirm: "Your complaint has been filed successfully! The manager will visit on {date} at {time}."

IMPORTANT RULES:
- Always collect ALL 4 pieces of information: flat_number, category, description, appointment_datetime
- Convert dates to ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
- For "tomorrow at 3pm" → Calculate exact date → "2026-02-09T15:00:00"
- Confirm each detail back to the user before submitting
- Be empathetic and conversational
- If user says "urgent" or "emergency", schedule for same day or next day if possible
```

## Testing the Flow

### Test Case 1: Happy Path
```
User: "My flat is 101"
Vapi: "Hi Pooja! What can I help you with?"
User: "The kitchen sink is leaking badly"
Vapi: "I understand, that's a plumbing issue. Can you describe it in more detail?"
User: "Water is dripping from under the sink constantly"
Vapi: "When would you like the manager to visit?"
User: "Tomorrow afternoon at 2 PM"
Vapi: [Calls submit_complaint with appointment_datetime="2026-02-09T14:00:00"]
Vapi: "Your complaint has been filed! The manager will visit tomorrow at 2 PM."
```

### Expected Database Results
After the call:
- ✅ Complaint created with description, category, flat_uuid, tenant_uuid
- ✅ Appointment created with scheduled_at, complaint_uuid, flat_uuid
- ✅ Call log created with transcript

## Webhook Behavior

The webhook now:
1. ✅ Receives `appointment_datetime` instead of `priority`
2. ✅ Sets default priority to "medium" for all voice complaints
3. ✅ Creates complaint first (gets complaint_uuid back)
4. ✅ Creates appointment using complaint_uuid + flat_uuid
5. ✅ Links appointment to complaint automatically

## Date/Time Parsing

Vapi's AI will handle natural language:
- "tomorrow at 3" → Next day at 15:00
- "Friday morning" → Next Friday at 10:00
- "in 2 days at 2pm" → Calculates exact datetime

All converted to ISO format before sending to webhook.

## Error Handling

If appointment creation fails:
- ✅ Complaint is still created
- ⚠️ Warning logged: "Appointment creation failed"
- User still gets confirmation (complaint filed)
- Manager can manually schedule later

This ensures robust behavior even if appointment logic has issues.

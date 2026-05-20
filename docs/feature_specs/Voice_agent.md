### **Complaint intake agent**
```json
{
  "id": "2cbc056b-c8b6-4406-97dd-4173604b249d",
  "orgId": "501aa737-9b8b-4088-b011-b29bb5e315b7",
  "name": "Complaint Intake Agent",
  "voice": {
    "model": "eleven_turbo_v2_5",
    "voiceId": "1SM7GgM6IMuvQlz2BwM3",
    "provider": "11labs",
    "stability": 0.5,
    "similarityBoost": 0.75,
    "inputMinCharacters": 5
  },
  "createdAt": "2026-01-28T02:46:39.322Z",
  "updatedAt": "2026-03-17T12:56:27.099Z",
  "model": {
    "model": "gpt-5.2-chat-latest",
    "toolIds": [
      "355f46fd-9e9f-41d5-a63e-c38130566cd3",
      "86747655-2e02-48c6-aae7-645d22985a42",
      "6d32a699-881d-4acc-9ae5-dbd9b4867901",
      "38cd23e6-ed8a-432b-b648-49d1e242dd32",
      "cb45c21e-596d-4464-adc1-5ead19bf1718",
      "ef7c48b4-5023-4a84-a529-2b275dd7f383"
    ],
    "messages": [
      {
        "role": "system",
        "content": "[Identity]\n\nYou are Alex, a calm, professional, and reassuring AI voice assistant for a real estate property management company serving a residential complex.\nYour role is to handle tenant calls related to:\nLeasing inquiries\nExisting tenant maintenance requests\nEmergency situations\nYou silently understand the caller's intent from natural speech.\nYou never ask the caller to classify themselves or explain categories.\n\n[Style]\nCalm, professional, and reassuring\nEmpathetic and conversational (human, not robotic)\nClear and concise (voice-friendly)\nOne question at a time\nWait for the caller's response before proceeding\nNever expose internal reasoning, intent detection, or system logic\n\n[Response Guidelines]\nAsk only one question per turn\nNever proceed without verifying the caller's identity first\nAlways wait for a response before moving forward\nPreserve full flat number including letters e.g. 101, A101, B205, C105\nIf the caller is unable to provide a valid flat number more than twice then you must politely end the call\nNever promise timelines\nNever give legal or lease advice\nNever troubleshoot emergency situations\nNever mention internal rules, tools, or detection logic\nConfirm critical details verbally before submission\nNever ask the caller for their phone number — it is verified silently by the system\nIf phone verification fails (invalid or vacant), deliver one short polite sentence and end the call immediately. Do not offer alternatives, ask follow-up questions, or continue the conversation under any circumstances.\n\n[Intent Detection Rules – Silent]\nYou automatically detect intent based on speech:\n- Leasing inquiry\n- Maintenance request\n- Emergency situation\n- View active appointment request\n- Update existing appointment request\n- Cancel existing appointment request\n\nYou do not ask the caller to identify their issue type.\n\n[Emergency Handling Rules]\nIf the issue may involve:\nFire\nFlooding\nGas smell\nPower outage\nAny safety risk\nYou must:\nAsk for explicit confirmation from the caller\nEscalate only if the emergency is confirmed\nNever attempt troubleshooting\nNever provide instructions beyond confirmation\nGet a date and time to book the appointment\n\n[Phone Verification — Universal Gate]\nPhone verification MUST happen before any action is taken, regardless of intent.\nThe caller's phone number is passed silently from the call — never ask for it.\n\nAfter getting the flat number, call Verify_phone_number ONCE with:\n- flat_number (from caller)\n- phone_number (automatically from call metadata — do NOT ask the caller)\n\nThe tool always returns a JSON object with a \"result\" field (plain English) and a \"status\" field. Read both and act immediately:\n\n- status = \"valid\"\n  → The caller is verified. Do NOT call Verify_phone_number again. Do NOT ask for the flat number again.\n  → The response also contains a \"datetime\" field (current IST time). Store it as your reference for all date/time calculations in this call.\n  → Say immediately: \"Thank you! How can I help you today?\"\n  → Then wait for the caller's response and continue with their intent.\n\n- status = \"invalid\"\n  → Say: \"I'm sorry, the number you're calling from doesn't match our records for that flat. Please contact our office directly. Have a good day.\"\n  → END CALL IMMEDIATELY. Do not ask follow-up questions. Do not retry verification.\n\n- status = \"vacant\"\n  → Say: \"I'm sorry, that flat doesn't appear to have a registered tenant. Please contact our office for assistance. Have a good day.\"\n  → END CALL IMMEDIATELY. Do not ask follow-up questions. Do not retry verification.\n\nCRITICAL: Verify_phone_number always returns one of the three statuses above. It never fails silently. Once you receive any status, act on it immediately and do not call Verify_phone_number again in the same call. The Verify_phone_number will also give a datetime and that will be the current date time so use that as reference in all cases\n\n[If Intent = View Active Appointment]\nAfter phone verification (see above):\nCall:\nview_active_appointments\nProvide:\nflat_number\nIf no appointments found:\nSay:\n\"There are currently no active appointments scheduled for your flat.\"\nIf appointments found:\nRead clearly:\nIssue category\nScheduled date\nScheduled time\nAsk:\n\"Would you like to make any changes to this appointment?\"\n<wait for response>\nIf yes → move to update flow\nIf no → end politely\n\n[If Intent = Update Existing Appointment]\nAfter phone verification (see above):\nCall:\nview_active_appointments\nIf none exist:\nInform user and stop.\nIf appointment exists:\nAsk:\n\"What new date and time would you prefer?\"\n<wait>\nSilently call check_availability with the proposed datetime.\nIf status = \"unavailable\":\nSay: \"I'm sorry, the manager already has an appointment around that time. Could you suggest another date or time?\"\n<wait> → loop back and ask for new time\nIf status = \"available\":\nConfirm before submission:\n\"Just to confirm, you'd like to reschedule your {category} appointment to {date} at {time}. Is that correct?\"\n<wait>\nThen call:\nupdate_appointment with:\nflat_number\nappointment_id (from view response)\nnew_appointment_datetime\nFinal confirmation:\n\"Your appointment has been successfully updated to {date} at {time}. If you need anything else, I'm here to help.\"\n\n[If Intent = Cancel Appointment]\nAfter phone verification (see above):\nCall:\nview_active_appointments\nProvide:\nflat_number\nIf no appointments found:\nSay: \"There are no active appointments to cancel for your flat.\" → end politely.\nIf appointments found:\nRead clearly:\nIssue category\nScheduled date\nScheduled time\nAsk: \"Which appointment would you like to cancel?\"\n<wait for response>\nConfirm before cancellation:\n\"Just to confirm, you'd like to cancel your {category} appointment on {date} at {time}. Is that correct?\"\n<wait>\nCall:\ncancel_appointment with:\nflat_number\nappointment id (from view response)\nFinal confirmation:\n\"Your appointment has been successfully cancelled. If you need anything else, I'm here to help.\"\n\n[Conversation Flow – Maintenance Requests]\n1. Greeting\nSay:\n\"Hello! I'm here to help with maintenance issues. What's your flat number?\"\n<wait for user response>\n\n2. Phone Verification\nCall Verify_phone_number with the flat_number provided and the caller's phone (automatic from call metadata).\nYou cannot proceed without a successful verification.\nIf the flat is not found in the database, ask the caller once more. If still not found, apologise and end the call.\nIf the caller is unable to provide a valid flat number more than twice, politely end the call.\nHandle Verify_phone_number results as described in [Phone Verification — Universal Gate].\nOn success, say: \"Thank you! How can I help you today?\"\n<wait for user response>\n\n3. Issue Identification\nSilently identify the issue category:\nPlumbing\nElectrical\nGeneral maintenance\nCleaning\nPest control\nOther\nAsk:\n\"Can you describe the issue in a bit more detail?\"\n<wait for user response>\n\n4. Appointment Scheduling\nAsk:\n\"When would you like the manager to visit? Please share a date and time.\"\n<wait for user response>\n\n5. Date & Time Processing\nUse the \"datetime\" value returned by Verify_phone_number as your reference for the current date and time.\nExtract appointment_datetime from natural language relative to that reference (2026 is the default year unless specified otherwise).\nConvert to ISO 8601 format:\nYYYY-MM-DDTHH:MM:SS\nExample:\n\"Tomorrow at 3 pm\" → 2026-02-09T15:00:00\n\nSilently call check_availability with the proposed datetime.\nIf status = \"unavailable\":\nSay: \"I'm sorry, the manager already has an appointment around that time. Could you suggest another date or time?\"\n<wait> → loop back to Step 4\nIf status = \"available\":\nProceed to Step 6.\n\n6. Confirmation Before Submission\nConfirm all four details clearly:\nFlat number\nIssue category\nIssue description\nAppointment date & time\nExample:\n\"Just to confirm, this is for flat 204, a plumbing issue involving leakage, scheduled for February 9th at 3 pm. Is that correct?\"\n<wait for confirmation>\n\n7. Complaint Submission\nCall submit_complaint with all required fields:\nflat_number\ncategory\ndescription\nappointment_datetime\n\n8. Final Confirmation\nSay:\n\"Your complaint has been filed successfully. The manager will visit on {date} at {time}. If there's anything else you need, I'm here to help.\"\n\n[Error Handling & Fallbacks]\nIf the caller's response is unclear, politely ask for clarification\nIf phone verification returns invalid or vacant, say one short polite sentence and end the call immediately. Do not re-attempt. Do not ask follow-up questions.\nIf a non-verification tool (submit_complaint, view_active_appointments, update_appointment, cancel_appointment, check_availability) returns an error or unexpected result, apologize briefly and ask the caller to repeat or reconfirm.\nVerify_phone_number always returns a valid status — never treat it as a failure. Always act on the status field immediately.\nAlways remain calm and reassuring\n\n[Tools Available]\nVerify_phone_number — Verifies that the caller's phone number matches the registered tenant of the flat. Returns: valid, invalid, or vacant. Phone number is passed automatically from call metadata — never ask the caller for it.\nsubmit_complaint — Webhook function to register maintenance complaints\nview_active_appointments — API tool to fetch scheduled appointments for a flat\nupdate_appointment — API tool to reschedule an existing appointment\ncancel_appointment — API tool to cancel an existing appointment\ncheck_availability — API tool to check whether the manager has a free slot at a requested datetime. Returns: available or unavailable.\n"
      }
    ],
    "provider": "openai",
    "maxTokens": 300,
    "temperature": 0.7
  },
  "firstMessage": "Hi, thanks for calling. This is Alex with the property management team of leadpipe Real Estate. How can I help you today?",
  "voicemailMessage": "Please call back",
  "endCallFunctionEnabled": true,
  "endCallMessage": "Thank you",
  "transcriber": {
    "model": "nova-3",
    "language": "en",
    "numerals": false,
    "provider": "deepgram",
    "fallbackPlan": {
      "transcribers": [
        {
          "model": "gpt-4o-transcribe",
          "language": "en",
          "provider": "openai"
        }
      ]
    },
    "confidenceThreshold": 0.4
  },
  "clientMessages": [
    "conversation-update",
    "function-call",
    "hang",
    "model-output",
    "speech-update",
    "status-update",
    "transfer-update",
    "transcript",
    "tool-calls",
    "user-interrupted",
    "voice-input",
    "workflow.node.started",
    "assistant.started"
  ],
  "serverMessages": [
    "conversation-update",
    "end-of-call-report",
    "function-call",
    "hang",
    "speech-update",
    "status-update",
    "tool-calls",
    "transfer-destination-request",
    "handoff-destination-request",
    "user-interrupted",
    "assistant.started"
  ],
  "endCallPhrases": [
    "goodbye",
    "talk to you soon"
  ],
  "hipaaEnabled": false,
  "backgroundSound": "office",
  "backgroundDenoisingEnabled": true,
  "artifactPlan": {
    "structuredOutputIds": [
      "e91b4670-4a5a-46d9-8507-3ac549fec4de"
    ]
  },
  "startSpeakingPlan": {
    "waitSeconds": 0.4,
    "smartEndpointingEnabled": "livekit"
  },
  "compliancePlan": {
    "hipaaEnabled": false,
    "pciEnabled": false,
    "zdrEnabled": false
  },
  "isServerUrlSecretSet": false
}
```
### Tool
**Verify_phone_number**
```json
{
  "id": "ef7c48b4-5023-4a84-a529-2b275dd7f383",
  "createdAt": "2026-03-17T12:38:01.486Z",
  "updatedAt": "2026-03-17T14:07:52.196Z",
  "type": "apiRequest",
  "function": {
    "name": "api_request_tool",
    "description": "this tool is used to used to verify the flat number the called says by matching the phone number from the which the call comes."
  },
  "messages": [
    {
      "type": "request-start",
      "blocking": false
    }
  ],
  "orgId": "501aa737-9b8b-4088-b011-b29bb5e315b7",
  "name": "Verify_phone_number",
  "url": "https://tenant-management-mvp.onrender.com/flats/verify-phone?phone_number={{customer.number}}",
  "method": "POST",
  "body": {
    "type": "object",
    "required": [
      "flat_number"
    ],
    "properties": {
      "flat_number": {
        "description": "Flat number provided by the caller",
        "type": "string",
        "default": ""
      }
    }
  },
  "variableExtractionPlan": {
    "schema": {
      "type": "object",
      "required": [
        "result",
        "status",
        "datetime"
      ],
      "properties": {
        "result": {
          "description": "",
          "type": "string"
        },
        "status": {
          "description": "",
          "type": "string"
        },
        "datetime": {
          "description": "",
          "type": "string"
        }
      }
    }
  }
}
```
**Check_availability**
```json
{
  "id": "38cd23e6-ed8a-432b-b648-49d1e242dd32",
  "createdAt": "2026-03-16T04:38:55.508Z",
  "updatedAt": "2026-03-17T14:08:01.980Z",
  "type": "apiRequest",
  "function": {
    "name": "api_request_tool",
    "description": "it sends the date and time the caller wants to make appointment on and it returns if the manager has any appointment at that date and time or not"
  },
  "messages": [
    {
      "type": "request-start",
      "blocking": false
    }
  ],
  "orgId": "501aa737-9b8b-4088-b011-b29bb5e315b7",
  "async": false,
  "name": "check_availability",
  "url": "https://tenant-management-mvp.onrender.com/appointments/availability?appointment_date={{datetime}}",
  "method": "GET",
  "body": {
    "type": "object",
    "required": [
      "datetime"
    ],
    "properties": {
      "datetime": {
        "description": "date/time in format YYYY-MM-DDTHH:MM:SS",
        "type": "string",
        "default": ""
      }
    }
  },
  "variableExtractionPlan": {
    "schema": {
      "type": "object",
      "required": [
        "status"
      ],
      "properties": {
        "status": {
          "description": "",
          "type": "string"
        }
      }
    }
  }
}
```
**cancel_appointment**
```json
{
  "id": "cb45c21e-596d-4464-adc1-5ead19bf1718",
  "createdAt": "2026-03-14T06:42:15.443Z",
  "updatedAt": "2026-03-17T14:08:20.383Z",
  "type": "apiRequest",
  "function": {
    "name": "api_request_tool",
    "description": "Cancel appointment"
  },
  "messages": [
    {
      "type": "request-start",
      "blocking": false
    }
  ],
  "orgId": "501aa737-9b8b-4088-b011-b29bb5e315b7",
  "async": false,
  "name": "cancel_appointment",
  "url": "https://tenant-management-mvp.onrender.com/appointments/cancel?id={{id}}&flat_number={{flat_number}}",
  "method": "PATCH",
  "body": {
    "type": "object",
    "required": [
      "id",
      "flat_number"
    ],
    "properties": {
      "id": {
        "description": "Primary key of the appointment",
        "type": "number",
        "default": ""
      },
      "flat_number": {
        "description": "Flat number the appointment belongs to",
        "type": "string",
        "default": ""
      }
    }
  },
  "variableExtractionPlan": {
    "schema": {
      "type": "object",
      "required": [
        "id",
        "status"
      ],
      "properties": {
        "id": {
          "description": "",
          "type": "integer"
        },
        "status": {
          "description": "",
          "type": "string"
        }
      }
    }
  }
}
```
**update_appointment**
```json
{
  "id": "6d32a699-881d-4acc-9ae5-dbd9b4867901",
  "createdAt": "2026-03-01T10:36:59.028Z",
  "updatedAt": "2026-03-17T14:08:28.697Z",
  "type": "apiRequest",
  "function": {
    "name": "api_request_tool",
    "description": "Update an appointment's details."
  },
  "messages": [
    {
      "type": "request-start",
      "blocking": false
    }
  ],
  "orgId": "501aa737-9b8b-4088-b011-b29bb5e315b7",
  "async": false,
  "name": "update_appointment",
  "url": "https://tenant-management-mvp.onrender.com/appointments/update?id={{id}}&flat_number={{flat_number}}&new_appointment_date={{new_appointment_date}}",
  "method": "PATCH",
  "body": {
    "type": "object",
    "required": [
      "flat_number",
      "id",
      "new_appointment_date"
    ],
    "properties": {
      "id": {
        "description": "Primary key of the appointment",
        "type": "number",
        "default": ""
      },
      "flat_number": {
        "description": "Flat number the appointment belongs to",
        "type": "string",
        "default": ""
      },
      "new_appointment_date": {
        "description": "New scheduled date/time in format YYYY-MM-DDTHH:MM:SS",
        "type": "string",
        "default": ""
      }
    }
  },
  "variableExtractionPlan": {
    "schema": {
      "type": "object",
      "required": [
        "id",
        "new_appointment_date"
      ],
      "properties": {
        "id": {
          "description": "",
          "type": "integer"
        },
        "new_appointment_date": {
          "description": "",
          "type": "string"
        }
      }
    }
  }
}
```
**view_active_appointments**
```json
{
  "id": "86747655-2e02-48c6-aae7-645d22985a42",
  "createdAt": "2026-02-28T16:32:50.967Z",
  "updatedAt": "2026-03-17T14:08:36.733Z",
  "type": "apiRequest",
  "function": {
    "name": "api_request_tool",
    "description": " API tool to fetch scheduled appointments for a flat"
  },
  "messages": [
    {
      "type": "request-start",
      "blocking": false
    }
  ],
  "orgId": "501aa737-9b8b-4088-b011-b29bb5e315b7",
  "async": false,
  "name": "view_active_appointments",
  "url": "https://tenant-management-mvp.onrender.com/appointments/view?flat_number={{flat_number}}",
  "method": "GET",
  "body": {
    "type": "object",
    "required": [],
    "properties": {
      "flat_number": {
        "description": "flat number whose appointments are being asked for by the caller",
        "type": "string",
        "default": ""
      }
    }
  },
  "variableExtractionPlan": {
    "schema": {
      "type": "object",
      "required": [
        "id",
        "appointment_date",
        "status"
      ],
      "properties": {
        "id": {
          "description": "",
          "type": "integer"
        },
        "status": {
          "description": "",
          "type": "string"
        },
        "category": {
          "description": "",
          "type": "string"
        },
        "appointment_id": {
          "description": "",
          "type": "string"
        },
        "appointment_date": {
          "description": "",
          "type": "string"
        }
      }
    }
  }
}
```
**submit_complaint**
```json
{
  "id": "355f46fd-9e9f-41d5-a63e-c38130566cd3",
  "createdAt": "2026-01-28T05:00:11.138Z",
  "updatedAt": "2026-03-17T14:08:45.048Z",
  "type": "function",
  "function": {
    "name": "submit_complaint",
    "strict": true,
    "description": "Submit a complaint after collecting flat number, category, description, and preferred appointment date/time from the caller",
    "parameters": {
      "type": "object",
      "properties": {
        "category": {
          "description": "- Allowed values ONLY: water, electricity, cleaning, noise, maintenance, security, other\r\n- Must be lowercase\r\n- If you can confidently extract category from the user's description, do so automatically\r\n- If extraction is uncertain or ambiguous, ask the user to choose from the allowed list. Allowed list = [\r\n    \"water\",\r\n    \"electricity\",\r\n    \"cleaning\",\r\n    \"noise\",\r\n    \"maintenance\",\r\n    \"security\",\r\n    \"other\"\r\n]",
          "type": "string",
          "enum": [
            "water, electricity, cleaning, noise, maintenance, security, other"
          ],
          "default": ""
        },
        "description": {
          "description": "Detailed description of the issue",
          "type": "string",
          "default": ""
        },
        "flat_number": {
          "description": "The flat/apartment number (e.g., '101', 'A105','B201','C201')",
          "type": "string",
          "default": ""
        },
        "appointment_date": {
          "description": "ISO 8601 datetime for when the manager should visit (e.g., '2026-02-10T15:00:00' for Feb 10 at 3 PM)",
          "type": "string",
          "default": ""
        }
      },
      "required": [
        "category",
        "flat_number",
        "appointment_date",
        "description"
      ]
    }
  },
  "messages": [
    {
      "type": "request-start",
      "blocking": false
    }
  ],
  "orgId": "501aa737-9b8b-4088-b011-b29bb5e315b7",
  "server": {
    "url": "https://tenant-management-mvp.onrender.com/voice/webhook",
    "timeoutSeconds": 20
  },
  "async": true,
  "variableExtractionPlan": {
    "schema": {
      "type": "object",
      "required": [],
      "properties": {}
    }
  }
}
```
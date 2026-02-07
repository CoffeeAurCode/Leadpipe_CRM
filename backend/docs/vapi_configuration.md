# Vapi Configuration Guide - UPDATED

## The Problem: "Failed to perform variable extraction"

This error means Vapi couldn't parse the URL template `{flat_no}`. Different solutions:

---

## ✅ SOLUTION 1: Use Query Parameter Endpoint (RECOMMENDED)

### Backend Endpoint
```
GET /tenants/by-flat-query?flat_no=101
```

### Vapi Configuration
```json
{
  "type": "function",
  "function": {
    "name": "lookup_tenant",
    "description": "Validates flat number and retrieves tenant information",
    "parameters": {
      "type": "object",
      "properties": {
        "flat_no": {
          "type": "string",
          "description": "The flat/apartment number to lookup"
        }
      },
      "required": ["flat_no"]
    }
  },
  "server": {
    "url": "https://YOUR-NGROK-URL.ngrok.io/tenants/by-flat-query",
    "method": "GET"
  }
}
```

**How it works:**
- Vapi automatically converts function parameters to query params
- `flat_no` from the function call becomes `?flat_no=VALUE`
- No URL template variables needed!

---

## SOLUTION 2: Use POST Instead (Alternative)

Some voice platforms prefer POST for API tools.

### Backend Endpoint
We can create a POST version if needed:
```
POST /tenants/lookup
Body: {"flat_no": "101"}
```

### Vapi Configuration
```json
{
  "type": "function",
  "function": {
    "name": "lookup_tenant",
    "parameters": {
      "type": "object",
      "properties": {
        "flat_no": {"type": "string"}
      },
      "required": ["flat_no"]
    }
  },
  "server": {
    "url": "https://YOUR-NGROK-URL.ngrok.io/tenants/lookup",
    "method": "POST"
  }
}
```

---

## Testing the Query Parameter Endpoint

### Direct Test
```bash
curl "https://YOUR-NGROK-URL.ngrok.io/tenants/by-flat-query?flat_no=101"
```

### Python Test
```bash
cd backend
python -c "import requests; print(requests.get('http://localhost:8000/tenants/by-flat-query?flat_no=101').json())"
```

### Expected Response
```json
{
  "exists": true,
  "flat_no": "101",
  "tenant": {
    "name": "Pooja Desai",
    "phone": "+91-9876543225"
  }
}
```

---

## Updated System Prompt for Vapi

```
You are a property management assistant.

When the caller mentions their flat number:
1. Extract the flat number from their speech
2. Call lookup_tenant with the flat_no parameter
3. Check the response:
   - If exists = true: Say "Hi {tenant.name} from flat {flat_no}!"
   - If exists = false: Say "I couldn't find that flat. Please repeat the number."
   
Always validate the flat before taking appointment requests.
```

---

## Troubleshooting

### Still getting variable extraction error?
- Make sure you're using `/by-flat-query` (query param version)
- NOT `/by-flat/{flat_no}` (path param version)

### Want to verify it works?
```bash
# Test locally first
curl "http://localhost:8000/tenants/by-flat-query?flat_no=101"

# Then test via ngrok
curl "https://YOUR-NGROK-URL.ngrok.io/tenants/by-flat-query?flat_no=101"
```

### Response still wrong?
Check Vapi's expected response schema matches:
```json
{
  "exists": "boolean",
  "flat_no": "string",
  "tenant": {
    "name": "string",
    "phone": "string"
  }
}
```

---

## Both Endpoints Available

You now have **2 endpoints** for flexibility:

1. **Path parameter**: `/tenants/by-flat/{flat_no}`
   - Use for: REST APIs, curl, direct HTTP calls
   
2. **Query parameter**: `/tenants/by-flat-query?flat_no=VALUE`
   - Use for: Vapi, external tools that auto-convert params

Both are identical in behavior - stateless, idempotent, always return 200.

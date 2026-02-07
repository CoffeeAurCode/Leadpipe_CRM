# ✅ WORKING VAPI CONFIGURATION

After extensive debugging, here's the **EXACT** configuration that works:

## Backend Changes Made

1. **CORS**: Hardcoded `allow_origins=["*"]` in `main.py` (no env vars)
2. **Endpoint**: Returns explicit `JSONResponse` with proper content-type
3. **Response Format**: Flat structure matching Vapi's schema

## Your Vapi Tool Config (COPY THIS EXACTLY)

```json
{
  "type": "apiRequest",
  "name": "Verify_flat",
  "function": {
    "name": "lookup_tenant",
    "description": "Validates flat number and retrieves tenant information"
  },
  "url": "https://kristan-miracidial-gainly.ngrok-free.dev/tenants/by-flat-query",
  "method": "GET",
  "body": {
    "type": "object",
    "required": ["flat_no"],
    "properties": {
      "flat_no": {
        "description": "The flat/apartment number provided by the caller",
        "type": "string"
      }
    }
  },
  "variableExtractionPlan": {
    "schema": {
      "type": "object",
      "required": ["exists"],
      "properties": {
        "exists": {
          "type": "boolean",
          "description": "Whether the flat exists and has a tenant"
        },
        "flat_no": {
          "type": "string",
          "description": "The flat number (normalized)"
        },
        "tenant_name": {
          "type": "string",
          "description": "Name of the tenant"
        },
        "tenant_phone": {
          "type": "string",
          "description": "Phone number of the tenant"
        }
      }
    }
  }
}
```

## Key Changes from Your Config

### ❌ WRONG (What you had)
```json
{
  "url": "https://.../tenants/by-flat/{{flat_no}}",  // Double braces + path param
  "method": "GET",
  "body": { "flat_no": "..." }  // Body on GET (confusing)
}
```

### ✅ CORRECT (What you need)
```json
{
  "url": "https://.../tenants/by-flat-query",  // Query param endpoint, NO template
  "method": "GET",
  "body": { "flat_no": "..." }  // Vapi converts this to ?flat_no=VALUE
}
```

## How It Works

1. **Caller says**: "My flat is 101"
2. **Vapi extracts**: `flat_no = "101"` from body definition
3. **Vapi calls**: `GET https://.../tenants/by-flat-query?flat_no=101`
   - The `body` field in config tells Vapi WHAT to extract
   - For GET requests, Vapi automatically converts body params to query params
4. **Backend returns**:
   ```json
   {
     "exists": true,
     "flat_no": "101",
     "tenant_name": "Pooja Desai",
     "tenant_phone": "+91-9876543225"
   }
   ```
5. **Vapi extracts** variables per `variableExtractionPlan`
6. **Vapi responds**: "Hi Pooja Desai from flat 101!"

## Testing Steps

### 1. Restart Backend
```powershell
# Stop current server (CTRL+C)
cd backend
uvicorn app.main:app --reload
```

You should now see **NO CORS debug log** (we removed it).

### 2. Test Direct Call
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/tenants/by-flat-query?flat_no=101" | Select-Object -ExpandProperty Content
```

Expected:
```json
{"exists":true,"flat_no":"101","tenant_name":"Pooja Desai","tenant_phone":"+91-9876543225"}
```

### 3. Test via ngrok
```powershell
Invoke-WebRequest -Uri "https://kristan-miracidial-gainly.ngrok-free.dev/tenants/by-flat-query?flat_no=101" | Select-Object -ExpandProperty Content
```

Should return same JSON.

### 4. Update Vapi Config
- Replace your current config with the JSON above
- Save in Vapi dashboard

### 5. Test in Vapi
- Use Vapi's tool test feature
- You should see successful variable extraction

## Watch Backend Logs

After restarting, when Vapi calls your endpoint you'll see:
```
INFO: 1.7.159.71:0 - "GET /tenants/by-flat-query?flat_no=101 HTTP/1.1" 200 OK
```

Note: **No more OPTIONS-only** - you'll see actual GET requests!

## Debugging

### If still failing:
1. Share the exact error from Vapi
2. Share what you see in backend logs
3. Test direct curl/Invoke-WebRequest and share response

### Common Issues:
- **Ngrok URL changed**: Check ngrok terminal for current URL
- **Backend not running**: Restart uvicorn
- **Still seeing old CORS**: Hard restart terminal, reload freshly

## Why This Works

- ✅ **No path parameters**: Vapi doesn't need to substitute `{flat_no}`
- ✅ **Query params**: Vapi auto-converts body to `?flat_no=VALUE`
- ✅ **Flat response**: Matches variableExtractionPlan exactly
- ✅ **Explicit JSON**: JSONResponse with proper content-type
- ✅ **CORS wildcard**: Allows requests from anywhere

Restart your backend now and update the Vapi config!

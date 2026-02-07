# Vapi Variable Extraction - Debugging Guide

## ✅ Changes Made

Updated the endpoint to return **explicit JSONResponse** with proper headers to ensure Vapi can parse the response.

### What Changed
- Added `from fastapi.responses import JSONResponse`
- All responses now use `JSONResponse()` with explicit `Content-Type: application/json` header
- All values explicitly converted to strings (`str()`)

## Test the Endpoint

### 1. Direct Test (via localhost)
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/tenants/by-flat/101" -Method GET | Select-Object -ExpandProperty Content
```

Expected output:
```json
{"exists":true,"flat_no":"101","tenant_name":"Pooja Desai","tenant_phone":"+91-9876543225"}
```

### 2. Via ngrok (what Vapi calls)
```powershell
Invoke-WebRequest -Uri "https://kristan-miracidial-gainly.ngrok-free.dev/tenants/by-flat/101" -Method GET | Select-Object -ExpandProperty Content
```

Should return the same JSON.

### 3. Check Response Headers
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/tenants/by-flat/101" -Method GET | Select-Object StatusCode, @{Name="ContentType";Expression={$_.Headers["Content-Type"]}}
```

Expected:
- StatusCode: 200
- ContentType: application/json

## Your Vapi Config Should Be

```json
{
  "url": "https://kristan-miracidial-gainly.ngrok-free.dev/tenants/by-flat/{flat_no}",
  "method": "GET",
  "variableExtractionPlan": {
    "schema": {
      "type": "object",
      "required": ["exists"],
      "properties": {
        "exists": {"type": "boolean"},
        "flat_no": {"type": "string"},
        "tenant_name": {"type": "string"},
        "tenant_phone": {"type": "string"}
      }
    }
  }
}
```

## Common Issues & Fixes

### Issue 1: "Unable to extract variable"
**Cause:** Response format doesn't match `variableExtractionPlan` schema

**Fix:** ✅ We now return exact format with explicit types:
```json
{
  "exists": true,          ← boolean (required)
  "flat_no": "101",        ← string
  "tenant_name": "...",    ← string
  "tenant_phone": "..."    ← string
}
```

### Issue 2: Path parameter not substituting
**Cause:** Vapi doesn't always substitute `{flat_no}` in path

**Solution:** If this persists, use query parameter version:
- URL: `https://.../tenants/by-flat-query`
- Add `parameters` field (Vapi will append `?flat_no=VALUE`)

### Issue 3: CORS errors
**Fix:** ✅ Already fixed - `allow_origins=["*"]`

## Verify in Terminal

Watch the backend logs for incoming requests:
```
INFO:     1.7.159.71:0 - "OPTIONS /tenants/by-flat/101 HTTP/1.1" 200 OK  ← CORS preflight
INFO:     1.7.159.71:0 - "GET /tenants/by-flat/101 HTTP/1.1" 200 OK      ← Actual request
```

If you see OPTIONS but NOT GET, that means:
- CORS passes ✅
- But the actual GET request is failing ❌

Check logs for errors during GET request.

## Next Steps

1. **Save your Vapi config** with the current URL
2. **Test in Vapi tool test** - should now extract variables correctly
3. **Check backend logs** - you should see GET requests (not just OPTIONS)
4. If still failing, share:
   - The exact error from Vapi
   - Backend logs when you test
   - Response you get from direct curl/Invoke-WebRequest

## Expected Flow

```
User in Vapi: "My flat is 101"
  ↓
Vapi extracts: flat_no = "101"
  ↓
Vapi calls: GET https://.../tenants/by-flat/101
  ↓
Backend returns: {"exists":true,"flat_no":"101","tenant_name":"Pooja Desai","tenant_phone":"+91-9876543225"}
  ↓
Vapi extracts variables:
  - exists = true
  - flat_no = "101"
  - tenant_name = "Pooja Desai"  
  - tenant_phone = "+91-9876543225"
  ↓
Vapi uses in conversation: "Hi Pooja Desai from flat 101!"
```

The server has auto-reloaded with the fix. Test again in Vapi! 🎯

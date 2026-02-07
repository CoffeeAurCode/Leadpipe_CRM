# Vapi Integration Testing Guide

## ✅ CORS Issue Fixed!

The endpoint now allows requests from **any origin**, including Vapi's testing tools.

## Testing with Vapi Tool Test Feature

### 1. Get Your ngrok URL
Your ngrok tunnel is running. Get the public URL:
```
Look at the ngrok terminal output for the HTTPS URL
Example: https://abc123.ngrok.io
```

### 2. Configure Vapi API Request Tool

In Vapi dashboard, configure the API Request Tool:

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
    "url": "https://YOUR-NGROK-URL.ngrok.io/tenants/by-flat/{flat_no}",
    "method": "GET"
  }
}
```

### 3. Test in Vapi

**Test Input:** `flat_no = "101"`

**Expected Response:**
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

**Test Input:** `flat_no = "999"` (non-existent)

**Expected Response:**
```json
{
  "exists": false
}
```

## System Prompt Example for Vapi

```
You are a helpful property management assistant.

When a caller says their flat number:
1. Use the lookup_tenant function to validate it
2. If exists = true, greet them: "Hi {tenant.name} from flat {flat_no}! How can I help you today?"
3. If exists = false, say: "I couldn't find that flat number in our system. Could you please repeat it?"

Never proceed without validating the flat number first.
```

## Troubleshooting

### "Network error: Unable to connect"
✅ **FIXED** - CORS now allows all origins

### ngrok URL not working
- Verify ngrok is running: `ngrok http 8000`
- Check the HTTPS URL (not HTTP)
- Ensure backend is running: `uvicorn app.main:app --reload`

### Backend not responding
```bash
# Check if backend is running
curl https://YOUR-NGROK-URL.ngrok.io/

# Should return: {"status": "Backend running"}
```

### Test the endpoint directly
```bash
# Via ngrok (from anywhere)
curl https://YOUR-NGROK-URL.ngrok.io/tenants/by-flat/101

# Via localhost (from your machine)
curl http://localhost:8000/tenants/by-flat/101
```

## CORS Settings

**Before (restrictive):**
```python
allow_origins=["http://localhost:5173", "..."]  # Only specific domains
allow_credentials=True
```

**After (Vapi-friendly):**
```python
allow_origins=["*"]  # All origins allowed
allow_credentials=False  # Required when using "*"
```

This is **safe** for stateless API endpoints like tenant lookup.

## Production Considerations

For production, consider:
1. Use a proper domain instead of ngrok
2. Add API key authentication for Vapi
3. Rate limiting to prevent abuse
4. Request logging for debugging
5. Optionally restrict CORS to Vapi's IP ranges

## Next Steps

1. ✅ CORS fixed - Vapi can now access the endpoint
2. Configure the tool in Vapi dashboard
3. Test the tool from Vapi
4. Update your system prompt to use the lookup_tenant function
5. Test end-to-end conversation flow

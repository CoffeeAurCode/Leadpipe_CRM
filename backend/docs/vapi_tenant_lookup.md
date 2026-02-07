# Vapi Tenant Lookup Endpoint

## Endpoint
```
GET /tenants/by-flat/{flat_no}
```

## Purpose
Stateless, idempotent endpoint for Vapi voice system to validate flat numbers and retrieve tenant information.

## Request Example
```bash
GET /tenants/by-flat/A-512
GET /tenants/by-flat/101
```

## Response Format

### ✅ Flat exists with active tenant
```json
{
  "exists": true,
  "flat_no": "A-512",
  "tenant": {
    "name": "Rahul Sharma",
    "phone": "+91XXXXXXXXXX"
  }
}
```

### ❌ Flat not found OR no tenant assigned
```json
{
  "exists": false
}
```

## Key Features

### 1. Always Returns 200
- **Never** returns 404, 500, or any error status
- Non-200 responses break Vapi conversation flow
- AI logic depends on boolean checks, not HTTP codes

### 2. Stateless & Pure
- No session state
- No conversation history
- No previous request dependency
- Every request is fully self-contained
- Read-only operation (no database writes)

### 3. Idempotent
- Same input **always** returns same output
- Can be called 10 times with no side effects
- No race conditions or state corruption

### 4. Input Normalization
Flat number is automatically:
- **Trimmed** of whitespace
- **Converted** to uppercase

Examples:
- `" a-512 "` → `"A-512"`
- `"101"` → `"101"`
- `" flat 101 "` → `"FLAT 101"`

### 5. Deterministic
Response derived **only** from request input, nothing else.

## Error Handling

All errors return:
```json
{
  "exists": false
}
```

Errors never leak to caller:
- Database failures
- Network issues
- Invalid data

Errors are logged internally for debugging.

## Database Logic

```
1. Normalize flat_no (trim + uppercase)
2. Query flats table: WHERE flat_number = normalized_flat_no
3. If flat not found → return {"exists": false}
4. Query tenants table: WHERE flat_uuid = flat.uuid
5. If no tenant → return {"exists": false}
6. If tenant found → return {"exists": true, ...}
```

## What This Endpoint Does

✅ Validates flat number exists  
✅ Retrieves tenant info for confirmation  
✅ Provides boolean result for AI logic  

## What This Endpoint Does NOT Do

❌ Create appointments  
❌ Reserve dates  
❌ Mutate database  
❌ Trigger side effects  
❌ Depend on conversation state  

## Testing

Run the test script:
```bash
# Start backend
cd backend
uvicorn app.main:app --reload

# In another terminal
python test_vapi_endpoint.py
```

Tests verify:
- Always returns 200
- Response has 'exists' field
- Normalization works
- Idempotent behavior
- No side effects

## Vapi Integration

### System Prompt Example
```
When the user says their flat number, use the lookup_tenant tool 
to verify it exists. 

If exists = true, confirm: "I found your flat {flat_no}. 
Is this you, {tenant.name}?"

If exists = false, say: "I couldn't find that flat number. 
Can you please repeat it?"
```

### API Request Tool Config
```json
{
  "type": "api",
  "url": "https://your-backend.com/tenants/by-flat/{flat_no}",
  "method": "GET",
  "response": {
    "exists": "boolean",
    "tenant": {
      "name": "string",
      "phone": "string"
    }
  }
}
```

## Production Considerations

1. **Rate Limiting**: Add rate limiting to prevent abuse
2. **Caching**: Consider caching flat/tenant lookups (with TTL)
3. **Logging**: Log all requests for debugging
4. **Monitoring**: Track failure rate of flat lookups
5. **Analytics**: Monitor which flats are frequently queried

## Why This Design Prevents Continuity Errors

### ❌ Bad (Stateful)
```python
# BAD: Depends on previous request
if session.flat_validated:
    return tenant_info
```

### ✅ Good (Stateless)
```python
# GOOD: Derives everything from input
flat = lookup_flat(flat_no)
tenant = lookup_tenant(flat.uuid)
return {"exists": bool(tenant)}
```

## Example Vapi Conversation Flow

```
User: "My flat is A-512"
Vapi: [Calls GET /tenants/by-flat/A-512]
Response: {"exists": true, "tenant": {"name": "Rahul"}}
Vapi: "Hi Rahul from flat A-512! How can I help?"

User: "I need maintenance"
Vapi: "What kind of maintenance do you need?"
[No dependency on previous lookup - conversation continues independently]
```

## File Location
[tenants.py](file:///c:/Users/BIT/Coding/Tenant_management_MVP/backend/app/routes/tenants.py#L19-L107)

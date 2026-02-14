# Manager Notification System - Environment Variables

## Required Environment Variables

Add these to your `.env` file:

### Twilio SMS Configuration
```bash
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890  # Your Twilio phone number
```

**How to get Twilio credentials:**
1. Sign up at https://www.twilio.com/
2. Go to Console → Account Info
3. Copy Account SID and Auth Token
4. Buy a phone number or use trial number
5. Paste values in .env

---

### SendGrid Email Configuration
```bash
SENDGRID_API_KEY=your_sendgrid_api_key_here
SENDGRID_FROM_EMAIL=noreply@yourdomain.com  # Verified sender email
MANAGER_EMAIL=manager@example.com  # Manager's email address
```

**How to get SendGrid API Key:**
1. Sign up at https://sendgrid.com/
2. Go to Settings → API Keys
3. Create a new API key with "Mail Send" permission
4. Add and verify sender email in Sender Authentication
5. Paste values in .env

---

## Manager Contact Information

The system currently sends notifications to:
- **SMS**: +919998064026 (hardcoded in notifications.py, line 147)
- **Email**: Value from MANAGER_EMAIL environment variable

**To change manager phone number:**
Edit `backend/app/services/notifications.py`, line 147:
```python
manager_phone = "+919998064026"  # Change this number
```

Or better yet, add to environment variables:
```bash
MANAGER_PHONE=+919998064026
```

And update the code to use:
```python
manager_phone = os.getenv("MANAGER_PHONE", "+919998064026")
```

---

## Complete .env Example

```bash
# Existing variables
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Twilio SMS
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+15551234567

# SendGrid Email
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=noreply@tenantmanagement.com
MANAGER_EMAIL=manager@example.com
```

---

## Dependencies Required

Install the required packages:

```bash
pip install twilio sendgrid
```

Or add to `requirements.txt`:
```
twilio>=8.0.0
sendgrid>=6.0.0
```

Then run:
```bash
pip install -r requirements.txt
```

---

## Testing Notifications

The system automatically sends notifications when:
1. An appointment is created via `POST /appointments`
2. The appointment is successfully saved to the database

**Notification behavior:**
- Notifications run in the background (non-blocking)
- If SMS fails, appointment is still created
- If Email fails, appointment is still created
- Errors are logged but don't affect the API response

**To test:**
```bash
curl -X POST http://localhost:8000/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "flat_number": "A101",
    "appointment_date": "2026-02-15T10:00:00",
    "notes": "Test appointment",
    "status": "scheduled"
  }'
```

Check your phone and email for notifications!

---

## Troubleshooting

### No SMS received:
- Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are correct
- Verify TWILIO_PHONE_NUMBER format (+<country><number>)
- Check Twilio console for error logs
- If using trial account, verify recipient number is verified

### No email received:
- Check SENDGRID_API_KEY is valid
- Verify SENDGRID_FROM_EMAIL is verified in SendGrid
- Check MANAGER_EMAIL is correct
- Look in spam folder
- Check SendGrid activity logs

### Check backend logs:
```bash
# Look for notification-related logs
tail -f backend.log | grep -i notification
```

Or check uvicorn console output for error messages.

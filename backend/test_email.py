import os, sys
sys.path.insert(0, '.')

with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

from_email = os.getenv('SENDGRID_FROM_EMAIL')
to_email = os.getenv('MANAGER_EMAIL')
print(f"FROM: {from_email}")
print(f"TO:   {to_email}")
print()

# Send via SendGrid directly so we can inspect the full response
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
message = Mail(
    from_email=Email(from_email),
    to_emails=To(to_email),
    subject='[LIVE TEST] Tenant Appointment Notification',
    html_content=Content("text/html", "<h2>Appointment Scheduled</h2><p>This is a live test of the notification system. If you see this, email delivery is working.</p>")
)

try:
    response = sg.send(message)
    print(f"Status Code: {response.status_code}")
    print(f"Body: {response.body}")
    print(f"Headers: {dict(response.headers)}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    if hasattr(e, 'body'):
        print(f"Response body: {e.body}")

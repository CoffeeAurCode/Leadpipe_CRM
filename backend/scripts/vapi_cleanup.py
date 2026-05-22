"""
One-time cleanup: deletes unused VAPI assistant and phone number.
Run from repo root: python backend/scripts/vapi_cleanup.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    from vapi import Vapi
except ImportError:
    print("ERROR: vapi SDK not installed.")
    sys.exit(1)

TOKEN = os.getenv("PRIVATE_VAPI_API")
if not TOKEN:
    print("ERROR: PRIVATE_VAPI_API not set in .env")
    sys.exit(1)

UNUSED_ASSISTANT_ID = "53bc5d25-73d8-4eef-b17b-865b643dc051"  # Lease Agent Test property(walkthrough)
UNUSED_NUMBER_ID    = "64ab1868-7ac6-4746-9cc2-3a689add6ea1"  # +15183189117

client = Vapi(token=TOKEN)

print("Deleting unused assistant:", UNUSED_ASSISTANT_ID)
client.assistants.delete(UNUSED_ASSISTANT_ID)
print("  Done.")

print("Deleting unused phone number:", UNUSED_NUMBER_ID)
client.phone_numbers.delete(UNUSED_NUMBER_ID)
print("  Done.")

print("\nCleanup complete.")

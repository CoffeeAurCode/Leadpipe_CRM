"""
Run from repo root: python backend/scripts/vapi_inspect.py
Lists all VAPI assistants and phone numbers, flags which are referenced in .env.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    from vapi import Vapi
except ImportError:
    print("ERROR: vapi SDK not installed. Run: pip install vapi-server-sdk")
    sys.exit(1)

TOKEN = os.getenv("PRIVATE_VAPI_API")
if not TOKEN:
    print("ERROR: PRIVATE_VAPI_API not set in .env")
    sys.exit(1)

ENV_ASSISTANT_IDS = {
    os.getenv("VAPI_ASSISTANT_ID"):          "VAPI_ASSISTANT_ID (legacy/outbound complaint)",
    os.getenv("VAPI_COMPLAINT_ASSISTANT_ID"): "VAPI_COMPLAINT_ASSISTANT_ID",
    os.getenv("VAPI_SHARED_LEASE_ASSISTANT_ID"): "VAPI_SHARED_LEASE_ASSISTANT_ID",
}

ENV_NUMBER_IDS = {
    os.getenv("VAPI_NUMBER_ID"):             "VAPI_NUMBER_ID",
    os.getenv("VAPI_COMPLAINT_NUMBER_ID"):   "VAPI_COMPLAINT_NUMBER_ID",
    os.getenv("VAPI_SHARED_LEASE_NUMBER_ID"): "VAPI_SHARED_LEASE_NUMBER_ID",
}

client = Vapi(token=TOKEN)

print("\n" + "="*60)
print("VAPI ASSISTANTS")
print("="*60)
assistants = client.assistants.list()
for a in assistants:
    tag = ENV_ASSISTANT_IDS.get(a.id, "NOT IN .env — CANDIDATE FOR DELETION")
    print(f"  [{a.id}]  {a.name or '(unnamed)'}")
    print(f"    > {tag}")
    print()

print("="*60)
print("VAPI PHONE NUMBERS")
print("="*60)
numbers = client.phone_numbers.list()
for n in numbers:
    tag = ENV_NUMBER_IDS.get(n.id, "NOT IN .env — CANDIDATE FOR DELETION")
    number_str = getattr(n, "number", None) or getattr(n, "phone_number", None) or "?"
    status = getattr(n, "status", "?")
    print(f"  [{n.id}]  {number_str}  (status: {status})")
    print(f"    > {tag}")
    print()

print("="*60)
print("SUMMARY — OUTBOUND COMPLAINT CALL PATH")
print("="*60)
print(f"  assistant_id used : {os.getenv('VAPI_ASSISTANT_ID')} (VAPI_ASSISTANT_ID)")
print(f"  phone_number_id   : {os.getenv('VAPI_NUMBER_ID')} (VAPI_NUMBER_ID)")
print(f"  complaint asst    : {os.getenv('VAPI_COMPLAINT_ASSISTANT_ID')} (NOT used for outbound)")
print()

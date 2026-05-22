"""
Register a Twilio-owned phone number into VAPI and add it to the twilio_number_pool.

Usage:
    python backend/scripts/add_twilio_number_to_vapi.py +15551234567
    python backend/scripts/add_twilio_number_to_vapi.py +15551234567 --notes "US East pool"

Prerequisites:
    - Number must already be purchased in the Twilio console
    - PRIVATE_VAPI_API, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN must be set in .env
    - twilio_number_pool table must exist (run migration 014)
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.config import settings
from supabase import create_client


def main():
    parser = argparse.ArgumentParser(
        description="Register a Twilio number in VAPI and add it to the provisioning pool"
    )
    parser.add_argument("phone_number", help="E.164 Twilio number, e.g. +15551234567")
    parser.add_argument("--notes", default="", help="Optional notes for this pool entry")
    args = parser.parse_args()

    number = args.phone_number.strip()
    if not number.startswith("+") or not number[1:].isdigit():
        print(f"ERROR: phone_number must be E.164 format (e.g. +15551234567). Got: {number}")
        sys.exit(1)

    if not settings.PRIVATE_VAPI_API:
        print("ERROR: PRIVATE_VAPI_API is not set in .env")
        sys.exit(1)
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        print("ERROR: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in .env")
        sys.exit(1)

    from vapi import Vapi
    from vapi.phone_numbers.types import CreatePhoneNumbersRequest_Twilio

    client = Vapi(token=settings.PRIVATE_VAPI_API)

    print(f"Registering {number} into VAPI as a Twilio-owned number...")
    try:
        phone = client.phone_numbers.create(
            request=CreatePhoneNumbersRequest_Twilio(
                provider="twilio",
                number=number,
                twilio_account_sid=settings.TWILIO_ACCOUNT_SID,
                twilio_auth_token=settings.TWILIO_AUTH_TOKEN,
            )
        )
    except Exception as e:
        print(f"ERROR: VAPI registration failed: {e}")
        sys.exit(1)

    print(f"VAPI registered: id={phone.id}  number={phone.number}")

    db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    try:
        db.table("twilio_number_pool").insert({
            "phone_number": phone.number,
            "vapi_phone_number_id": phone.id,
            "status": "available",
            "notes": args.notes,
        }).execute()
    except Exception as e:
        print(f"ERROR: DB insert failed: {e}")
        print(f"NOTE: The number was registered in VAPI with id={phone.id}. Delete it manually if you need to retry.")
        sys.exit(1)

    print(f"\nDone. {phone.number} is available in the pool for auto-assignment.")
    print(f"  VAPI phone number ID : {phone.id}")
    print(f"  Pool status          : available")


if __name__ == "__main__":
    main()

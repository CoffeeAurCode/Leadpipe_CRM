from vapi import Vapi
import os
from dotenv import load_dotenv

load_dotenv()

client = Vapi(token=os.getenv("PRIVATE_VAPI_API"))

LEASE_ASSISTANT_ID = os.getenv("VAPI_SHARED_LEASE_ASSISTANT_ID")
COMPLAINT_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")

for assistant_id in filter(None, [LEASE_ASSISTANT_ID, COMPLAINT_ASSISTANT_ID]):
    result = client.assistants.update(
        assistant_id,
        end_call_function_enabled=True,
    )
    print(f"Updated {result.id}: endCallFunctionEnabled={result.end_call_function_enabled}")

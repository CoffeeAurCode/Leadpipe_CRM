"""
Quick test to check what the endpoint returns
"""
import sys
sys.path.insert(0, 'c:/Users/BIT/Coding/Tenant_management_MVP/backend')

# Test the endpoint response
import json

# Simulate what the endpoint should return
test_response = {
    "exists": True,
    "flat_no": "101",
    "tenant_name": "Pooja Desai",
    "tenant_phone": "+91-9876543225"
}

print("Expected Vapi Response Format:")
print(json.dumps(test_response, indent=2))

print("\n" + "="*60)
print("Test the actual endpoint with:")
print("curl http://localhost:8000/tenants/by-flat/101")
print("\nor via ngrok:")
print("curl https://kristan-miracidial-gainly.ngrok-free.dev/tenants/by-flat/101")

import requests
import uuid

BASE_URL = "http://localhost:8000"

def test_add_flat_simple():
    print("\n--- Testing Add Flat (Simple) ---")
    flat_number = f"TEST-{uuid.uuid4().hex[:4].upper()}"
    payload = {
        "flat_number": flat_number,
        "address": "Test Building",
        "floor_number": 1,
        "bedrooms": 2
    }
    
    try:
        response = requests.post(f"{BASE_URL}/flats", data=payload)
        if response.status_code == 201:
            print(f"✅ Success: Created flat {flat_number}")
            print(response.json())
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_add_flat_with_tenant():
    print("\n--- Testing Add Flat (With Tenant) ---")
    flat_number = f"TEST-{uuid.uuid4().hex[:4].upper()}"
    payload = {
        "flat_number": flat_number,
        "address": "Test Building",
        "tenant_name": "Test Tenant",
        "tenant_phone": "1234567890"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/flats", data=payload)
        if response.status_code == 201:
            data = response.json()
            if data.get("tenant"):
                print(f"✅ Success: Created flat {flat_number} with tenant")
            else:
                 print(f"❌ Failed: Tenant not created")
            print(data)
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_add_flat_simple()
    test_add_flat_with_tenant()

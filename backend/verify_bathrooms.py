import requests
import json
import os

BASE_URL = "http://localhost:8000"

def log(msg, success=None):
    if success is True:
        print(f"[SUCCESS] {msg}")
    elif success is False:
        print(f"[FAILED] {msg}")
    else:
        print(f"[INFO] {msg}")

def verify_bathrooms():
    # 1. Create a flat with 3 bathrooms
    log("Step 1: Creating flat with 3 bathrooms...")
    files = {
        'flat_number': (None, 'BATH_TEST_01'),
        'floor_number': (None, '1'),
        'bedrooms': (None, '2'),
        'bathrooms': (None, '3'),
        'address': (None, 'Test Bath Building')
    }
    
    try:
        res = requests.post(f"{BASE_URL}/flats", files=files)
        if res.status_code != 200:
            log(f"Create failed: {res.text}", False)
            return
        
        flat_data = res.json()["flat"]
        flat_uuid = flat_data["uuid"]
        
        if flat_data.get("bathrooms") == 3:
            log("Flat created with bathrooms=3", True)
        else:
            log(f"Flat created but bathrooms={flat_data.get('bathrooms')}", False)
            return

        # 2. Verify GET /properties
        log("Step 2: Verifying GET /properties...")
        res = requests.get(f"{BASE_URL}/properties")
        props = res.json()
        target_prop = next((p for p in props if p["uuid"] == flat_uuid), None)
        
        if target_prop and target_prop.get("bathrooms") == 3:
            log("GET /properties returns correct bathrooms count", True)
        else:
            log(f"GET /properties failed. Found: {target_prop}", False)

        # 3. Update flat to 4 bathrooms
        log("Step 3: Updating flat to 4 bathrooms...")
        update_payload = {
            "action": "UPDATE_FLAT_ONLY",
            "flat_details": {
                "bedrooms": 2,
                "bathrooms": 4,
                "floor_number": 1,
                "address": "Test Bath Building"
            }
        }
        res = requests.patch(f"{BASE_URL}/flats/{flat_uuid}", json=update_payload)
        
        if res.status_code != 200:
            log(f"Update failed: {res.text}", False)
            return

        updated_flat = res.json()
        if updated_flat.get("bathrooms") == 4:
            log("Flat updated to bathrooms=4", True)
        else:
            log(f"Update returned bathrooms={updated_flat.get('bathrooms')}", False)

        # 4. Cleanup (optional, but good practice if delete endpoint existed)
        # For now we just leave it.

    except Exception as e:
        log(f"Exception during verification: {e}", False)

if __name__ == "__main__":
    verify_bathrooms()

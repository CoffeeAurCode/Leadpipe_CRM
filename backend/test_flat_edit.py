import requests
import json
import uuid

BASE_URL = "http://localhost:8000"

def log(msg, success=True):
    mark = "[OK]" if success else "[FAIL]"
    print(f"{mark} {msg}")

def test_flat_edit_system():
    print("Starting Flat Edit System Tests...\n")
    
    # Prerequisite: We need a test flat. 
    # For safety, let's pick a known 'availble' flat or create one if possible.
    # Since we can't easily create without potentially hitting unique constraints,
    # let's try to fetch a flat that is likely empty or use a specific test flat logic if we were in a test DB.
    # For this MVP verify, let's find a flat that is currently EMPTY.
    
    try:
        # 1. Find a vacant flat
        all_flats = requests.get(f"{BASE_URL}/flats").json()
        vacant_flat = next((f for f in all_flats if f.get('tenant_uuid') is None), None)
        
        if not vacant_flat:
            log("No vacant flat found to test 'Add Tenant'. Skipping.", False)
            return

        flat_uuid = vacant_flat['uuid']
        flat_number = vacant_flat['flat_number']
        print(f"Selected Test Flat: {flat_number} ({flat_uuid})")

        # TEST CASE 1: Add Tenant to Vacant Flat
        print(f"\n--- Test Case 1: Add Tenant to Flat {flat_number} ---")
        new_tenant_data = {
            "name": "Test User",
            "phone": f"555{uuid.uuid4().hex[:7]}" # Random phone to avoid unique constraint
        }
        
        payload_add = {
            "action": "ADD_TENANT",
            "tenant_data": new_tenant_data
        }
        
        res = requests.patch(f"{BASE_URL}/flats/{flat_uuid}", json=payload_add)
        
        if res.status_code == 200:
            updated_flat = res.json()
            if updated_flat.get('tenant_uuid'):
                log("Tenant added successfully.")
                tenant_uuid = updated_flat['tenant_uuid']
            else:
                log("Response 200 but tenant_uuid missing!", False)
                return
        else:
            log(f"Failed to add tenant: {res.text}", False)
            return

        # TEST CASE 2: Update Existing Tenant
        print(f"\n--- Test Case 2: Update Tenant in Flat {flat_number} ---")
        update_tenant_data = {
            "name": "Updated Name",
            "phone": new_tenant_data["phone"]
        }
        
        payload_update = {
            "action": "UPDATE_TENANT",
            "tenant_data": update_tenant_data
        }
        
        res = requests.patch(f"{BASE_URL}/flats/{flat_uuid}", json=payload_update)
        
        if res.status_code == 200:
            updated_tenant = res.json().get('tenant')
            if updated_tenant['name'] == "Updated Name":
                log("Tenant details updated successfully.")
            else:
                log(f"Tenant update mismatch: {updated_tenant}", False)
        else:
            log(f"Failed to update tenant: {res.text}", False)

        # TEST CASE 3: Update Flat Details Only
        print(f"\n--- Test Case 3: Update Flat Details Only ---")
        payload_flat = {
            "action": "UPDATE_FLAT_ONLY",
            "flat_details": {"bedrooms": 5}
        }
        
        res = requests.patch(f"{BASE_URL}/flats/{flat_uuid}", json=payload_flat)
        if res.status_code == 200:
            if res.json()['bedrooms'] == 5:
                log("Flat details updated successfully.")
            else:
                log("Flat details update failed to reflect.", False)
        else:
             log(f"Failed to update flat: {res.text}", False)

        # TEST CASE 4: Remove Tenant
        print(f"\n--- Test Case 4: Remove Tenant from Flat {flat_number} ---")
        payload_remove = {
            "action": "REMOVE_TENANT"
        }
        
        res = requests.patch(f"{BASE_URL}/flats/{flat_uuid}", json=payload_remove)
        
        if res.status_code == 200:
            if res.json().get('tenant_uuid') is None:
                log("Tenant removed successfully. Flat is vacant.")
            else:
                log("Tenant removal failed. UUID still present.", False)
        else:
            log(f"Failed to remove tenant: {res.text}", False)

        # CLEANUP: Restore bedroom count
        requests.patch(f"{BASE_URL}/flats/{flat_uuid}", json={
            "action": "UPDATE_FLAT_ONLY",
            "flat_details": {"bedrooms": vacant_flat.get('bedrooms')}
        })
        print("\nAll systems go!")

    except Exception as e:
        log(f"Test crashed: {e}", False)

if __name__ == "__main__":
    test_flat_edit_system()

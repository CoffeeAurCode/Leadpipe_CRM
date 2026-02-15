import http.client
import json
import uuid

BASE_URL = "localhost:8000"

def test_patch_update():
    print("\n--- Testing PATCH /flats/{uuid} ---")
    
    # 1. Create a flat first
    flat_number = f"PATCH-{uuid.uuid4().hex[:4].upper()}"
    boundary = '---BOUNDARY' + uuid.uuid4().hex
    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="flat_number"\r\n\r\n{flat_number}\r\n'
        f'--{boundary}--\r\n'
    )
    headers = {'Content-Type': f'multipart/form-data; boundary={boundary}'}
    
    conn = http.client.HTTPConnection(BASE_URL)
    conn.request("POST", "/flats", body, headers)
    resp = conn.getresponse()
    flat_data = json.loads(resp.read().decode())
    flat_uuid = flat_data["uuid"]
    print(f"Created flat: {flat_uuid}")
    
    # 2. Update Flat Details Only
    print("\n[Action: UPDATE_FLAT_ONLY]")
    payload = {
        "action": "UPDATE_FLAT_ONLY",
        "flat_details": {
            "bedrooms": 3
        }
    }
    conn.request("PATCH", f"/flats/{flat_uuid}", json.dumps(payload), {'Content-Type': 'application/json'})
    resp = conn.getresponse()
    data = resp.read().decode()
    
    if resp.status == 200:
        res_json = json.loads(data)
        if res_json["bedrooms"] == 3:
            print("OK: Flat details updated")
        else:
            print(f"FAIL: Flat details mismatch: {res_json}")
    else:
        print(f"FAIL: {resp.status} - {data}")

    # 3. Add Tenant
    print("\n[Action: ADD_TENANT]")
    payload = {
        "action": "ADD_TENANT",
        "tenant_data": {
            "name": "Patch Tenant",
            "phone": "9998887777"
        }
    }
    conn.request("PATCH", f"/flats/{flat_uuid}", json.dumps(payload), {'Content-Type': 'application/json'})
    resp = conn.getresponse()
    data = resp.read().decode()
    
    if resp.status == 200:
        res_json = json.loads(data)
        if res_json["tenant"]["name"] == "Patch Tenant" and res_json["tenant_uuid"]:
            print("OK: Tenant added and returned")
        else:
            print(f"FAIL: Tenant mismatch: {res_json}")
            
        # Check if occupied is True (implied by tenant_uuid presence in DB default)
        # Note: FlatResponse default for occupied is True, but check if we rely on tenant_uuid
        if res_json["tenant_uuid"]:
             print("OK: tenant_uuid present")
    else:
        print(f"FAIL: Failed: {resp.status} - {data}")


    conn.close()

if __name__ == "__main__":
    test_patch_update()

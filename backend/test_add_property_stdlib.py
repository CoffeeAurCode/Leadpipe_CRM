import http.client
import json
import uuid
import mimetypes
import time

BASE_URL = "localhost:8000"

def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

def encode_multipart_formdata(fields, files):
    boundary = '---BOUNDARY' + uuid.uuid4().hex
    crlf = b'\r\n'
    L = []
    
    for (key, value) in fields.items():
        L.append('--' + boundary)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(str(value))
        
    for (key, filename, filecontent) in files:
        L.append('--' + boundary)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
        L.append('Content-Type: %s' % get_content_type(filename))
        L.append('')
        L.append(filecontent)
        
    L.append('--' + boundary + '--')
    L.append('')
    body = crlf.join([x.encode('utf-8') if isinstance(x, str) else x for x in L])
    content_type = 'multipart/form-data; boundary=%s' % boundary
    return content_type, body

def test_add_flat_simple():
    print("\n--- Testing Add Flat (Simple) ---")
    flat_number = f"TEST-{uuid.uuid4().hex[:4].upper()}"
    fields = {
        "flat_number": flat_number,
        "address": "Test Building Standard Lib",
        "floor_number": 1,
        "bedrooms": 2
    }
    files = []
    
    content_type, body = encode_multipart_formdata(fields, files)
    
    try:
        conn = http.client.HTTPConnection(BASE_URL)
        headers = {'Content-Type': content_type}
        
        conn.request("POST", "/flats", body, headers)
        response = conn.getresponse()
        data = response.read().decode()
        
        if response.status == 201:
            print(f"SUCCESS: Created flat {flat_number}")
            print(data)
        else:
            print(f"FAILED: {response.status} - {data}")
        conn.close()
            
    except Exception as e:
        print(f"ERROR: {e}")

def test_add_flat_with_tenant():
    print("\n--- Testing Add Flat (With Tenant) ---")
    flat_number = f"TEST-{uuid.uuid4().hex[:4].upper()}"
    fields = {
        "flat_number": flat_number,
        "address": "Test Building Standard Lib",
        "floor_number": 1,
        "bedrooms": 2,
        "tenant_name": "Test Tenant StdLib",
        "tenant_phone": "1234567890"
    }
    files = []
    
    content_type, body = encode_multipart_formdata(fields, files)
    
    try:
        conn = http.client.HTTPConnection(BASE_URL)
        headers = {'Content-Type': content_type}
        
        conn.request("POST", "/flats", body, headers)
        response = conn.getresponse()
        data = response.read().decode()
        
        if response.status == 201:
            print(f"SUCCESS: Created flat {flat_number} with tenant")
            resp_json = json.loads(data)
            if resp_json.get("tenant") and resp_json["tenant"]["name"] == "Test Tenant StdLib":
                 print("✅ Tenant verified in response")
            else:
                 print("❌ Tenant missing in response")
            print(data)
        else:
            print(f"FAILED: {response.status} - {data}")
        conn.close()
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    # Wait a bit for server to be ready if just started
    time.sleep(2) 
    test_add_flat_simple()
    test_add_flat_with_tenant()

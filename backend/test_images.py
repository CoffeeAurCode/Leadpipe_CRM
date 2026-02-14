import requests

def test_properties_images():
    print("Testing GET /properties for image URLs...")
    try:
        response = requests.get("http://localhost:8000/properties")
        if response.status_code == 200:
            properties = response.json()
            print(f"Found {len(properties)} properties.")
            for prop in properties[:3]:  # Check first 3
                print(f"Property: {prop['name']}")
                print(f"  Image URL: {prop.get('image_url')}")
                if prop.get('image_url') and "assets" not in prop.get('image_url'):
                    print("  [OK] Valid external URL")
                else:
                    print("  [FAIL] potential local path or missing URL")
        else:
            print(f"[FAIL] API Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"[FAIL] Connection Failed: {e}")

if __name__ == "__main__":
    test_properties_images()

import requests
from app.db.session import get_db

def verify_occupancy_fix():
    print("Verifying occupancy... fetching API and DB data...")
    
    # 1. Fetch API data
    try:
        api_response = requests.get("http://localhost:8000/properties")
        api_props = {p['flat_number']: p for p in api_response.json()}
    except Exception as e:
        print(f"Failed to fetch API: {e}")
        return

    # 2. Fetch DB data
    db = get_db()
    db_response = db.table("flats").select("*").execute()
    db_flats = {f['flat_number']: f for f in db_response.data}
    
    print("-" * 80)
    print(f"{'Flat':<10} | {'DB Tenant':<36} | {'API Occupied':<12} | {'Correct?'}")
    print("-" * 80)
    
    mismatches = 0
    checked_count = 0
    
    for flat_num, db_flat in db_flats.items():
        if flat_num not in api_props:
            continue
            
        api_prop = api_props[flat_num]
        
        # Ground truth: Occupied only if tenant_uuid exists
        has_tenant = db_flat.get('tenant_uuid') is not None
        
        # API should reflect this
        api_says_occupied = api_prop['occupied']
        
        is_correct = (has_tenant == api_says_occupied)
        
        if not is_correct:
            mismatches += 1
            mark = "FAIL <---"
        else:
            mark = "OK"
            
        # Only print details for previously problematic flats or if mismatch
        # Problematic ones from previous run: B201, B202, B301, C101-C202, 101-105
        # Or just verify all
        
        if not is_correct or flat_num in ['B201', '101', 'C101']: 
             print(f"{flat_num:<10} | {str(db_flat.get('tenant_uuid')):<36} | {str(api_says_occupied):<12} | {mark}")
        
        checked_count += 1

    print("-" * 80)
    print(f"Checked {checked_count} flats.")
    if mismatches == 0:
        print("✅ SUCCESS: API occupancy logic matches DB tenant presence 100%.")
    else:
        print(f"❌ FAILURE: Found {mismatches} mismatches.")

if __name__ == "__main__":
    verify_occupancy_fix()

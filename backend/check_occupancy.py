from app.db.session import get_db

def check_occupancy_mismatch():
    db = get_db()
    response = db.table("flats").select("*").execute()
    
    print(f"Total flats: {len(response.data)}")
    print("-" * 60)
    print(f"{'Flat':<10} | {'Occupied Col':<12} | {'Tenant UUID':<36} | {'Mismatch?'}")
    print("-" * 60)
    
    mismatches = 0
    for flat in response.data:
        occupied_col = flat.get('occupied')
        tenant_uuid = flat.get('tenant_uuid')
        
        # User logic: Occupied if tenant_uuid IS NOT NULL
        is_actually_occupied = tenant_uuid is not None
        
        mismatch = occupied_col != is_actually_occupied
        if mismatch:
            mismatches += 1
            mark = "YES <--- BUG"
        else:
            mark = ""
            
        print(f"{flat['flat_number']:<10} | {str(occupied_col):<12} | {str(tenant_uuid):<36} | {mark}")

    print("-" * 60)
    print(f"Total mismatches found: {mismatches}")

if __name__ == "__main__":
    try:
        check_occupancy_mismatch()
    except Exception as e:
        print(f"Error: {e}")

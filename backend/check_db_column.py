from app.db.session import get_db
from supabase import Client

def check_flat_columns():
    db = get_db()
    response = db.table("flats").select("*").limit(1).execute()
    if response.data:
        flat = response.data[0]
        print("Flat keys:", flat.keys())
        if "image_url" in flat:
            print("image_url column EXISTS")
            print("Sample value:", flat["image_url"])
        else:
            print("image_url column MISSING")
    else:
        print("No flats found to check")

if __name__ == "__main__":
    check_flat_columns()

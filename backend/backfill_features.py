"""
Backfill Script: Initialize Feature Flags for Existing Properties

This script adds default feature flags for all existing properties that don't have them yet.
Run this after creating the property_features table.
"""

import os
import sys

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client, Client
from dotenv import load_dotenv
from app.core.features import Feature, get_default_state

# Load environment variables from .env in backend directory
load_dotenv()

# Initialize Supabase client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ Error: SUPABASE_URL or SUPABASE_KEY not found in environment")
    sys.exit(1)

db: Client = create_client(url, key)


def backfill_property_features():
    """Initialize default features for all existing properties"""
    
    print("=== Backfilling Property Feature Flags ===\n")
    
    # 1. Fetch all properties
    print("Fetching all properties...")
    properties_res = db.table("flats").select("uuid, flat_number").execute()
    properties = properties_res.data
    
    if not properties:
        print("⚠️  No properties found")
        return
    
    print(f"✅ Found {len(properties)} properties\n")
    
    # 2. Get list of features that should be enabled by default
    default_enabled_features = [
        feature for feature in Feature 
        if get_default_state(feature)
    ]
    
    print(f"Default enabled features: {[f.value for f in default_enabled_features]}\n")
    
    # 3. For each property, insert default feature flags
    success_count = 0
    skip_count = 0
    
    for prop in properties:
        property_uuid = prop["uuid"]
        flat_number = prop["flat_number"]
        
        print(f"Processing {flat_number} ({property_uuid})...")
        
        # Check if property already has feature flags
        existing = db.table("property_features")\
            .select("feature_key")\
            .eq("property_uuid", property_uuid)\
            .execute()
        
        if existing.data:
            print(f"  ↳ Already has {len(existing.data)} features, skipping")
            skip_count += 1
            continue
        
        # Insert default features
        try:
            rows_to_insert = [
                {
                    "property_uuid": property_uuid,
                    "feature_key": feature.value,
                    "enabled": True
                }
                for feature in default_enabled_features
            ]
            
            db.table("property_features").insert(rows_to_insert).execute()
            print(f"  ✅ Initialized {len(rows_to_insert)} default features")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n=== Summary ===")
    print(f"✅ Initialized: {success_count} properties")
    print(f"⏭️  Skipped: {skip_count} properties (already configured)")
    print(f"📊 Total: {len(properties)} properties")


if __name__ == "__main__":
    try:
        backfill_property_features()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)

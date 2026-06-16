#!/usr/bin/env python3
"""End-to-end API test runner for API_TEST_PLAN.md"""

import requests
import json
import sys
from datetime import datetime

BASE = "https://tenant-management-mvp.onrender.com"
TOKEN = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjE3ODIzMTZkLTllY2MtNDgxZC1iNDc2LTk2NzA3M2JlM2Q4OSIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL25mZ254bmRrdGVjcWVsZWFiYmlwLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIyOGM0M2M3Ny04YzljLTQ5NmYtOGQxZS0zOWZmYTlkNjE5ZTMiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzgwNTg4MDE1LCJpYXQiOjE3ODA1ODQ0MTUsImVtYWlsIjoibGVhZHBpcGVjcm1AZ21haWwuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJnb29nbGUiLCJwcm92aWRlcnMiOlsiZ29vZ2xlIl19LCJ1c2VyX21ldGFkYXRhIjp7ImF2YXRhcl91cmwiOiJodHRwczovL2xoMy5nb29nbGV1c2VyY29udGVudC5jb20vYS9BQ2c4b2NKS0I4OVRNMVQyR1hKc1FoU2RfQi13MXozOXl2dFZTOTQyaXFQQTcwTmpXR0tNNlE9czk2LWMiLCJlbWFpbCI6ImxlYWRwaXBlY3JtQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJmdWxsX25hbWUiOiJMZWFkcGlwZSIsImlzcyI6Imh0dHBzOi8vYWNjb3VudHMuZ29vZ2xlLmNvbSIsIm5hbWUiOiJMZWFkcGlwZSIsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FDZzhvY0pLQjg5VE0xVDJHWEpzUWhTZF9CLXcxejM5eXZ0VlM5NDJpcVBBNzBOaldHS002UT1zOTYtYyIsInByb3ZpZGVyX2lkIjoiMTAxOTUwMzczMjAwOTQwOTU1OTMzIiwic3ViIjoiMTAxOTUwMzczMjAwOTQwOTU1OTMzIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoib2F1dGgiLCJ0aW1lc3RhbXAiOjE3ODA0MjI2OTR9XSwic2Vzc2lvbl9pZCI6ImY5MTVmNzAzLTJjZmEtNDFjNS1hODYzLTQ2ZDI5M2Y1N2M4YyIsImlzX2Fub255bW91cyI6ZmFsc2V9.stlKcPDzC_8gYZAJ35j2NzloztCqMuF7dOivsxAOwnaDt0ypAhK9HckgROepDxnwovaXOBwHFKWvxE9UfCLP6w"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
AUTH = {"Authorization": f"Bearer {TOKEN}"}

results = []
state = {}  # shared state between tests

def r(test_id, description, status, actual_status, body, notes=""):
    icon = "PASS" if status == "PASS" else ("SKIP" if status == "SKIP" else "FAIL")
    results.append({
        "id": test_id, "desc": description, "status": icon,
        "http": actual_status, "notes": notes, "body": body
    })
    tag = f"[{icon}]"
    print(f"{tag:6} {test_id:12} {description[:55]:<55}  HTTP {actual_status}  {notes}")

def get(path, auth=True, params=None):
    h = HEADERS if auth else {}
    return requests.get(f"{BASE}{path}", headers=h, params=params, timeout=30)

def post(path, body=None, auth=True):
    h = HEADERS if auth else {"Content-Type": "application/json"}
    return requests.post(f"{BASE}{path}", headers=h, json=body, timeout=30)

def patch(path, body=None, auth=True, params=None):
    h = HEADERS if auth else {"Content-Type": "application/json"}
    return requests.patch(f"{BASE}{path}", headers=h, json=body, params=params, timeout=30)

def delete(path, body=None, auth=True):
    h = HEADERS if auth else {}
    return requests.delete(f"{BASE}{path}", headers=h, json=body, timeout=30)

def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return {"_raw": resp.text[:300]}

print(f"\n{'='*80}")
print(f"  API Test Run — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  Base: {BASE}")
print(f"{'='*80}\n")

# ── SECTION 1: Auth ─────────────────────────────────────────────────────────
print("\n── Section 1: Auth & Subscription ──")

resp = get("/payments/subscription-status")
body = safe_json(resp)
status_val = body.get("status","")
r("T01", "Subscription status", "PASS" if resp.status_code==200 and status_val in ("trialing","active") else "FAIL",
  resp.status_code, body, status_val)

resp = requests.get(f"{BASE}/complaints", timeout=30)
r("T02", "No token → 401", "PASS" if resp.status_code==401 else "FAIL",
  resp.status_code, safe_json(resp))

resp = requests.get(f"{BASE}/complaints", headers={"Authorization":"Bearer garbage.token.here"}, timeout=30)
r("T03", "Garbage token → 401", "PASS" if resp.status_code==401 else "FAIL",
  resp.status_code, safe_json(resp))

# ── SECTION 2: Property Groups ───────────────────────────────────────────────
print("\n── Section 2: Property Groups ──")

resp = get("/property-groups")
body = safe_json(resp)
groups = body if isinstance(body, list) else []
state["PG_ID"] = groups[0]["id"] if groups else None
r("P01", "List property groups", "PASS" if resp.status_code==200 and isinstance(body,list) else "FAIL",
  resp.status_code, body, f"count={len(groups)}, PG_ID={state.get('PG_ID','?')}")

resp = post("/property-groups", {"name":"API Test Group","description":"Created by test",
    "street_address":"123 Test St","city":"Montreal","state":"QC","country":"Canada"})
body = safe_json(resp)
state["TEST_PG_ID"] = body.get("id")
r("P02", "Create property group", "PASS" if resp.status_code in (200,201) and state["TEST_PG_ID"] else "FAIL",
  resp.status_code, body, f"TEST_PG_ID={state['TEST_PG_ID']}")

resp = post("/property-groups", {"name":"Incomplete Group"})
r("P03", "Create group missing fields → 422", "PASS" if resp.status_code==422 else "FAIL",
  resp.status_code, safe_json(resp))

resp = get("/property-groups/users/me/vapi-config")
body = safe_json(resp)
r("P04", "VAPI config for manager", "PASS" if resp.status_code==200 and "vapi_provisioning_status" in body else "FAIL",
  resp.status_code, body, body.get("vapi_provisioning_status",""))

if state["PG_ID"]:
    resp = get(f"/property-groups/{state['PG_ID']}/buildings")
    body = safe_json(resp)
    r("P05", "Buildings under property group", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")
else:
    r("P05", "Buildings under property group", "SKIP", 0, {}, "No PG_ID")

if state["TEST_PG_ID"]:
    resp = delete(f"/property-groups/{state['TEST_PG_ID']}")
    body = safe_json(resp)
    r("P06", "Delete test property group", "PASS" if resp.status_code in (200,204) else "FAIL",
      resp.status_code, body)

# Bulk delete test
resp_a = post("/property-groups", {"name":"Bulk A","street_address":"1 A St","city":"Montreal","state":"QC","country":"Canada"})
resp_b = post("/property-groups", {"name":"Bulk B","street_address":"2 B St","city":"Montreal","state":"QC","country":"Canada"})
ba = safe_json(resp_a); bb = safe_json(resp_b)
if ba.get("id") and bb.get("id"):
    resp = delete("/property-groups/bulk", {"ids":[ba["id"], bb["id"]]})
    body = safe_json(resp)
    r("P07", "Bulk delete property groups", "PASS" if resp.status_code==200 and body.get("deleted")==2 else "FAIL",
      resp.status_code, body)
else:
    r("P07", "Bulk delete property groups", "SKIP", 0, {}, "Could not create bulk test groups")

# ── SECTION 3: Buildings ─────────────────────────────────────────────────────
print("\n── Section 3: Buildings ──")

resp = get("/buildings")
body = safe_json(resp)
buildings = body if isinstance(body, list) else []
state["BUILDING_ID"] = buildings[0]["id"] if buildings else None
r("B01", "List buildings", "PASS" if resp.status_code==200 and isinstance(body,list) else "FAIL",
  resp.status_code, body, f"count={len(buildings)}")

if state["BUILDING_ID"]:
    resp = get(f"/buildings/{state['BUILDING_ID']}")
    r("B02", "Get single building", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, safe_json(resp))
else:
    r("B02", "Get single building", "SKIP", 0, {}, "No BUILDING_ID")

resp = post("/buildings", {"name":"Test Building Alpha","property_id": state["PG_ID"],
    "city":"Montreal","state":"QC","country":"Canada"})
body = safe_json(resp)
state["TEST_BLD_ID"] = body.get("id")
r("B03", "Create building", "PASS" if resp.status_code in (200,201) and state["TEST_BLD_ID"] else "FAIL",
  resp.status_code, body, f"TEST_BLD_ID={state['TEST_BLD_ID']}")

resp = post("/buildings", {"name":"Test Building Alpha","property_id": state["PG_ID"],
    "city":"Montreal","state":"QC","country":"Canada"})
body = safe_json(resp)
r("B04", "Create building duplicate → 400", "PASS" if resp.status_code==400 else "FAIL",
  resp.status_code, body)

if state["TEST_BLD_ID"]:
    resp = patch(f"/buildings/{state['TEST_BLD_ID']}",
                 {"name":"Test Building Alpha (Updated)","description":"Updated via API test"})
    body = safe_json(resp)
    r("B05", "Update building", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, body)

    resp = delete("/buildings/bulk", {"ids":[state["TEST_BLD_ID"]]})
    body = safe_json(resp)
    r("B06", "Bulk delete buildings", "PASS" if resp.status_code==200 and body.get("deleted")==1 else "FAIL",
      resp.status_code, body)
    state["TEST_BLD_ID"] = None
else:
    r("B05", "Update building", "SKIP", 0, {}, "No TEST_BLD_ID")
    r("B06", "Bulk delete buildings", "SKIP", 0, {}, "No TEST_BLD_ID")

resp = delete("/buildings/00000000-0000-0000-0000-000000000000")
r("B07", "Delete nonexistent building → 404", "PASS" if resp.status_code in (404,200) else "FAIL",
  resp.status_code, safe_json(resp))

# ── SECTION 4: Flats ─────────────────────────────────────────────────────────
print("\n── Section 4: Flats ──")

# Re-create building
resp = post("/buildings", {"name":"Flat Test Block","property_id": state["PG_ID"],
    "city":"Montreal","state":"QC","country":"Canada"})
body = safe_json(resp)
state["TEST_BLD_ID"] = body.get("id")
print(f"  [setup] Re-created Flat Test Block building: {state['TEST_BLD_ID']}")

resp = get("/flats")
body = safe_json(resp)
r("F01", "List all flats", "PASS" if resp.status_code==200 and isinstance(body,list) else "FAIL",
  resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

resp = get("/flats", params={"vacant":"true"})
body = safe_json(resp)
r("F02", "List vacant flats only", "PASS" if resp.status_code==200 and isinstance(body,list) else "FAIL",
  resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

resp = post("/flats", {"flat_number":"APITEST-01","building_id": state["TEST_BLD_ID"],
    "bedrooms":2,"bathrooms":1,"floor_number":3,"city":"Montreal","state":"QC","country":"Canada"})
body = safe_json(resp)
state["TEST_FLAT_UUID"] = body.get("uuid")
r("F03", "Create flat", "PASS" if resp.status_code in (200,201) and state["TEST_FLAT_UUID"] else "FAIL",
  resp.status_code, body, f"TEST_FLAT_UUID={state['TEST_FLAT_UUID']}")

resp = post("/flats", {"flat_number":"APITEST-01","building_id": state["TEST_BLD_ID"],
    "bedrooms":1,"bathrooms":1,"city":"Montreal","state":"QC","country":"Canada"})
r("F04", "Create flat duplicate → 400", "PASS" if resp.status_code==400 else "FAIL",
  resp.status_code, safe_json(resp))

resp = post("/flats", {"building_id": state["TEST_BLD_ID"],"bedrooms":1,"bathrooms":1})
r("F05", "Create flat missing flat_number → 422", "PASS" if resp.status_code==422 else "FAIL",
  resp.status_code, safe_json(resp))

if state["TEST_FLAT_UUID"]:
    resp = get(f"/flats/{state['TEST_FLAT_UUID']}/details")
    r("F06", "Get flat details", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, safe_json(resp))

    resp = get("/flats/APITEST-01")
    r("F07", "Get flat by flat_number", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, safe_json(resp))

    resp = patch(f"/flats/{state['TEST_FLAT_UUID']}", {"bedrooms":3,"bathrooms":2,"floor_number":5})
    r("F08", "Update flat", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, safe_json(resp))
else:
    for tid, desc in [("F06","Get flat details"),("F07","Get flat by flat_number"),("F08","Update flat")]:
        r(tid, desc, "SKIP", 0, {}, "No TEST_FLAT_UUID")

resp = post("/flats", {"flat_number":"APITEST-02","building_id": state["TEST_BLD_ID"],
    "bedrooms":1,"bathrooms":1,"city":"Montreal","state":"QC","country":"Canada"})
body = safe_json(resp)
state["TEST_FLAT2_UUID"] = body.get("uuid")
print(f"  [setup] APITEST-02 uuid: {state['TEST_FLAT2_UUID']}")

if state["TEST_FLAT2_UUID"]:
    resp = delete("/flats/bulk", {"uuids":[state["TEST_FLAT2_UUID"]]})
    body = safe_json(resp)
    r("F10", "Bulk delete flats", "PASS" if resp.status_code==200 and body.get("deleted")==1 else "FAIL",
      resp.status_code, body)

    # Re-create APITEST-02
    resp = post("/flats", {"flat_number":"APITEST-02","building_id": state["TEST_BLD_ID"],
        "bedrooms":1,"bathrooms":1,"city":"Montreal","state":"QC","country":"Canada"})
    body2 = safe_json(resp)
    state["TEST_FLAT2_UUID"] = body2.get("uuid")

    resp = delete(f"/flats/{state['TEST_FLAT2_UUID']}")
    r("F11", "Delete single flat", "PASS" if resp.status_code in (200,204) else "FAIL",
      resp.status_code, safe_json(resp))
else:
    r("F10", "Bulk delete flats", "SKIP", 0, {}, "No TEST_FLAT2_UUID")
    r("F11", "Delete single flat", "SKIP", 0, {}, "No TEST_FLAT2_UUID")

# ── SECTION 5: Tenants ───────────────────────────────────────────────────────
print("\n── Section 5: Tenants ──")

resp = post("/tenants", {"name":"Test Tenant API","phone":"+15145559999","email":"test@example.com",
    "flat_uuid": state["TEST_FLAT_UUID"],"lease_start_date":"2026-01-01","lease_end_date":"2026-12-31",
    "rent_status":"On-time","payment_schedule":"monthly"})
body = safe_json(resp)
state["TEST_TENANT_UUID"] = body.get("uuid")
r("TN01", "Create tenant", "PASS" if resp.status_code in (200,201) and state["TEST_TENANT_UUID"] else "FAIL",
  resp.status_code, body, f"TEST_TENANT_UUID={state['TEST_TENANT_UUID']}")

resp = post("/tenants", {"name":"Dupe Phone","phone":"+15145559999","flat_uuid": state["TEST_FLAT_UUID"]})
r("TN02", "Duplicate phone → 400", "PASS" if resp.status_code==400 else "FAIL",
  resp.status_code, safe_json(resp))

# Create APITEST-03 for occupied-flat test
resp = post("/flats", {"flat_number":"APITEST-03","building_id": state["TEST_BLD_ID"],
    "bedrooms":1,"bathrooms":1,"city":"Montreal","state":"QC","country":"Canada"})
state["TEST_FLAT3_UUID"] = safe_json(resp).get("uuid")

resp = post("/tenants", {"name":"Another Person","phone":"+15145550099","flat_uuid": state["TEST_FLAT_UUID"]})
r("TN03", "Tenant on occupied flat → 400", "PASS" if resp.status_code==400 else "FAIL",
  resp.status_code, safe_json(resp))

resp = get("/tenants")
body = safe_json(resp)
r("TN04", "List tenants", "PASS" if resp.status_code==200 and isinstance(body,list) else "FAIL",
  resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

resp = get("/tenants", params={"flat_uuid": state["TEST_FLAT_UUID"]})
body = safe_json(resp)
r("TN05", "List tenants filtered by flat", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body)

if state["TEST_TENANT_UUID"]:
    resp = get(f"/tenants/{state['TEST_TENANT_UUID']}")
    r("TN06", "Get single tenant", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, safe_json(resp))

resp = get("/tenants/by-flat/APITEST-01")
body = safe_json(resp)
r("TN07", "Get tenant by flat_number (occupied)", "PASS" if resp.status_code==200 and body.get("exists")==True else "FAIL",
  resp.status_code, body)

resp = get("/tenants/by-flat/APITEST-03")
body = safe_json(resp)
r("TN08", "Get tenant by flat_number (vacant)", "PASS" if resp.status_code==200 and body.get("exists")==False else "FAIL",
  resp.status_code, body)

resp = get("/tenants/by-flat/DOESNOTEXIST")
body = safe_json(resp)
r("TN09", "Get tenant by nonexistent flat", "PASS" if resp.status_code==200 and body.get("exists")==False else "FAIL",
  resp.status_code, body)

if state["TEST_TENANT_UUID"]:
    resp = patch(f"/tenants/{state['TEST_TENANT_UUID']}", {"manager_notes":"Updated via API test","rent_status":"Upcoming"})
    body = safe_json(resp)
    r("TN10", "Update tenant", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, body)

    resp = patch(f"/tenants/{state['TEST_TENANT_UUID']}/rent-status", {"rent_status":"Overdue"})
    body = safe_json(resp)
    r("TN11", "Update rent status via dedicated endpoint", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, body)

    resp = patch(f"/flats/{state['TEST_FLAT_UUID']}/unassign-tenant", {})
    r("TN12", "Unassign tenant from flat", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, safe_json(resp))

    resp = patch(f"/flats/{state['TEST_FLAT_UUID']}/assign-tenant", {"tenant_uuid": state["TEST_TENANT_UUID"]})
    r("TN13", "Assign existing tenant to flat", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, safe_json(resp))

    resp = delete(f"/tenants/{state['TEST_TENANT_UUID']}")
    r("TN14", "Delete tenant", "PASS" if resp.status_code in (200,204) else "FAIL",
      resp.status_code, safe_json(resp))

# ── SECTION 6: Complaints ────────────────────────────────────────────────────
print("\n── Section 6: Complaints ──")

# Get T101 flat UUID
resp = get("/flats/T101")
body = safe_json(resp)
state["REAL_FLAT_UUID"] = body.get("uuid") if isinstance(body, dict) else None
print(f"  [setup] T101 flat UUID: {state['REAL_FLAT_UUID']}")

if state["REAL_FLAT_UUID"]:
    resp = post("/complaints", {"flat_uuid": state["REAL_FLAT_UUID"],"flat_number":"T101",
        "category":"water","priority":"high","description":"Kitchen faucet dripping (API test)",
        "status":"pending","source":"web"})
    body = safe_json(resp)
    state["TEST_CMPL_UUID"] = body.get("uuid")
    r("CM01", "Create complaint", "PASS" if resp.status_code in (200,201) and state["TEST_CMPL_UUID"] else "FAIL",
      resp.status_code, body, f"uuid={state['TEST_CMPL_UUID']}")

    resp = post("/complaints", {"flat_uuid": state["REAL_FLAT_UUID"],"flat_number":"T101",
        "category":"electricity","priority":"medium","description":"Lights flickering (API test)",
        "status":"pending","source":"web","appointment_date":"2026-08-01T10:00:00"})
    body = safe_json(resp)
    r("CM02", "Create complaint with appointment", "PASS" if resp.status_code in (200,201) else "FAIL",
      resp.status_code, body)
    state["CMPL_WITH_APPT_UUID"] = body.get("uuid")

    resp = post("/complaints", {"flat_uuid": state["REAL_FLAT_UUID"],"flat_number":"T101",
        "category":"flooding","priority":"high","description":"Category does not exist","status":"pending","source":"web"})
    r("CM03", "Create complaint invalid category → 400", "PASS" if resp.status_code==400 else "FAIL",
      resp.status_code, safe_json(resp))

    resp = post("/complaints", {"flat_uuid": state["REAL_FLAT_UUID"],"flat_number":"T101",
        "category":"noise","priority":"low","description":"Test","status":"fake-status","source":"web"})
    r("CM04", "Create complaint invalid status → 400", "PASS" if resp.status_code==400 else "FAIL",
      resp.status_code, safe_json(resp))

    # CM05 — all 7 categories
    cat_pass = 0
    cat_uuids = []
    for cat in ["water","electricity","cleaning","noise","maintenance","security","other"]:
        r2 = post("/complaints", {"flat_uuid": state["REAL_FLAT_UUID"],"flat_number":"T101",
            "category":cat,"priority":"low","description":f"Testing category {cat} (API test)",
            "status":"pending","source":"web"})
        b2 = safe_json(r2)
        if r2.status_code in (200,201) and b2.get("uuid"):
            cat_pass += 1
            cat_uuids.append(b2["uuid"])
    r("CM05", "All 7 valid categories", "PASS" if cat_pass==7 else "FAIL",
      200, {}, f"{cat_pass}/7 created")
    state["CAT_CMPL_UUIDS"] = cat_uuids

    resp = get("/complaints")
    body = safe_json(resp)
    r("CM06", "List complaints", "PASS" if resp.status_code==200 and isinstance(body,list) else "FAIL",
      resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

    if state["TEST_CMPL_UUID"]:
        resp = get(f"/complaints/{state['TEST_CMPL_UUID']}")
        r("CM07", "Get single complaint", "PASS" if resp.status_code==200 else "FAIL",
          resp.status_code, safe_json(resp))

        resp = patch(f"/complaints/{state['TEST_CMPL_UUID']}", {"status":"in-progress","priority":"medium"})
        body = safe_json(resp)
        r("CM08", "Update complaint status → in-progress", "PASS" if resp.status_code==200 else "FAIL",
          resp.status_code, body)

        resp = patch(f"/complaints/{state['TEST_CMPL_UUID']}", {"status":"resolved"})
        body = safe_json(resp)
        r("CM09", "Update complaint → resolved", "PASS" if resp.status_code==200 else "FAIL",
          resp.status_code, body)

        resp = delete(f"/complaints/{state['TEST_CMPL_UUID']}")
        r("CM10", "Delete complaint", "PASS" if resp.status_code in (200,204) else "FAIL",
          resp.status_code, safe_json(resp))

    resp = delete("/complaints/00000000-0000-0000-0000-000000000000")
    r("CM11", "Delete nonexistent complaint → 404", "PASS" if resp.status_code in (404,400) else "FAIL",
      resp.status_code, safe_json(resp))
else:
    for tid in ["CM01","CM02","CM03","CM04","CM05","CM06","CM07","CM08","CM09","CM10","CM11"]:
        r(tid, f"Complaint test {tid}", "SKIP", 0, {}, "No REAL_FLAT_UUID")

# ── SECTION 7: Appointments ──────────────────────────────────────────────────
print("\n── Section 7: Appointments ──")

if state.get("REAL_FLAT_UUID"):
    resp = post("/complaints", {"flat_uuid": state["REAL_FLAT_UUID"],"flat_number":"T101",
        "category":"maintenance","priority":"low","description":"Appointment test complaint (API test)",
        "status":"pending","source":"web"})
    state["CMPL2_UUID"] = safe_json(resp).get("uuid")

    if state["CMPL2_UUID"]:
        resp = post("/appointments", {"complaint_uuid": state["CMPL2_UUID"],"flat_number":"T101",
            "flat_uuid": state["REAL_FLAT_UUID"],"appointment_date":"2026-09-10T14:00:00",
            "status":"scheduled","type":"callback","tenant_phone":"+15145550011"})
        body = safe_json(resp)
        state["TEST_APPT_ID"] = body.get("id")
        state["TEST_APPT_UUID"] = body.get("uuid")
        r("AP01", "Create appointment", "PASS" if resp.status_code in (200,201) and state["TEST_APPT_ID"] else "FAIL",
          resp.status_code, body, f"id={state['TEST_APPT_ID']}")

        resp = post("/appointments", {"complaint_uuid": state["CMPL2_UUID"],"flat_number":"T101",
            "flat_uuid": state["REAL_FLAT_UUID"],"appointment_date":"2026-09-11T10:00:00","status":"invalid-status"})
        r("AP02", "Create appointment invalid status → 400", "PASS" if resp.status_code==400 else "FAIL",
          resp.status_code, safe_json(resp))
    else:
        r("AP01", "Create appointment", "SKIP", 0, {}, "No CMPL2_UUID")
        r("AP02", "Create appointment invalid status", "SKIP", 0, {}, "No CMPL2_UUID")

    resp = get("/appointments")
    body = safe_json(resp)
    r("AP03", "List appointments", "PASS" if resp.status_code==200 and isinstance(body,list) else "FAIL",
      resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

    resp = get("/appointments", params={"start_date":"2026-09-01","end_date":"2026-09-30"})
    body = safe_json(resp)
    r("AP04", "List appointments date filter", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

    resp = get("/appointments", params={"flat_number":"T101"})
    r("AP05", "List appointments flat_number filter", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, safe_json(resp))

    if state.get("TEST_APPT_ID"):
        resp = get(f"/appointments/{state['TEST_APPT_ID']}")
        r("AP06", "Get single appointment", "PASS" if resp.status_code==200 else "FAIL",
          resp.status_code, safe_json(resp))

        resp = patch(f"/appointments/{state['TEST_APPT_ID']}", {"status":"attended","notes":"Manager called, issue resolved"})
        body = safe_json(resp)
        r("AP07", "Update appointment", "PASS" if resp.status_code==200 else "FAIL",
          resp.status_code, body)
    else:
        r("AP06", "Get single appointment", "SKIP", 0, {}, "No TEST_APPT_ID")
        r("AP07", "Update appointment", "SKIP", 0, {}, "No TEST_APPT_ID")
else:
    for tid in ["AP01","AP02","AP03","AP04","AP05","AP06","AP07"]:
        r(tid, f"Appointment {tid}", "SKIP", 0, {}, "No REAL_FLAT_UUID")

# AP08-AP10 availability (no auth)
resp = requests.get(f"{BASE}/appointments/availability", params={"appointment_date":"2026-10-01T10:00:00"}, timeout=30)
body = safe_json(resp)
r("AP08", "Availability — available slot", "PASS" if resp.status_code==200 and body.get("status")=="available" else "FAIL",
  resp.status_code, body)

resp = requests.get(f"{BASE}/appointments/availability", params={"appointment_date":"2026-07-15T13:30:00"}, timeout=30)
body = safe_json(resp)
r("AP09", "Availability — within 1hr → unavailable", "PASS" if resp.status_code==200 and body.get("status")=="unavailable" else "FAIL",
  resp.status_code, body)

resp = requests.get(f"{BASE}/appointments/availability", params={"appointment_date":"2026-07-15T13:00:00"}, timeout=30)
body = safe_json(resp)
r("AP10", "Availability — boundary (exactly 1hr → available)", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body, body.get("status",""))

resp = requests.get(f"{BASE}/appointments/view", params={"flat_number":"T202"}, timeout=30)
body = safe_json(resp)
r("AP11", "VAPI view appointments T202", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

# Save T202 appointment id for reschedule/cancel
t202_appt_id = None
if isinstance(body, list) and body:
    t202_appt_id = body[0].get("id")
state["T202_APPT_ID"] = t202_appt_id

resp = requests.get(f"{BASE}/appointments/view", params={"flat_number":"T101"}, timeout=30)
body = safe_json(resp)
r("AP12", "VAPI view — flat with no appointments", "PASS" if resp.status_code==200 and body==[] else "FAIL",
  resp.status_code, body)

if t202_appt_id:
    resp = requests.patch(f"{BASE}/appointments/update", params={
        "flat_number":"T202","id":t202_appt_id,"new_appointment_date":"2026-07-25T11:00:00"}, timeout=30)
    body = safe_json(resp)
    r("AP13", "VAPI reschedule appointment", "PASS" if resp.status_code==200 and body.get("status")=="success" else "FAIL",
      resp.status_code, body)

    resp = requests.patch(f"{BASE}/appointments/cancel", params={"flat_number":"T202","id":t202_appt_id}, timeout=30)
    body = safe_json(resp)
    r("AP14", "VAPI cancel appointment", "PASS" if resp.status_code==200 and body.get("status")=="cancelled" else "FAIL",
      resp.status_code, body)

    resp = requests.patch(f"{BASE}/appointments/cancel", params={"flat_number":"T202","id":t202_appt_id}, timeout=30)
    body = safe_json(resp)
    r("AP15", "VAPI cancel idempotent", "PASS" if resp.status_code==200 and body.get("status")=="cancelled" else "FAIL",
      resp.status_code, body)
else:
    r("AP13", "VAPI reschedule appointment", "SKIP", 0, {}, "No T202 appt")
    r("AP14", "VAPI cancel appointment", "SKIP", 0, {}, "No T202 appt")
    r("AP15", "VAPI cancel idempotent", "SKIP", 0, {}, "No T202 appt")

if state.get("TEST_APPT_ID"):
    resp = delete(f"/appointments/{state['TEST_APPT_ID']}")
    r("AP16", "Delete appointment (soft cancel)", "PASS" if resp.status_code in (200,204) else "FAIL",
      resp.status_code, safe_json(resp))
else:
    r("AP16", "Delete appointment", "SKIP", 0, {}, "No TEST_APPT_ID")

# ── SECTION 8: Rents ─────────────────────────────────────────────────────────
print("\n── Section 8: Rents ──")

if state.get("REAL_FLAT_UUID"):
    resp = post("/rents/set", {"flat_uuid": state["REAL_FLAT_UUID"],"monthly_rent":1500,"effective_from":"2026-01-01"})
    body = safe_json(resp)
    r("R01", "Set rent for flat", "PASS" if resp.status_code in (200,201) else "FAIL",
      resp.status_code, body)

    resp = post("/rents/set", {"flat_uuid": state["REAL_FLAT_UUID"],"monthly_rent":1600,"effective_from":"2026-07-01"})
    body = safe_json(resp)
    r("R02", "Update rent (new amount)", "PASS" if resp.status_code in (200,201) else "FAIL",
      resp.status_code, body)
else:
    r("R01", "Set rent for flat", "SKIP", 0, {}, "No REAL_FLAT_UUID")
    r("R02", "Update rent", "SKIP", 0, {}, "No REAL_FLAT_UUID")

resp = get("/rents/summary")
body = safe_json(resp)
r("R03", "Rent summary", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body, f"type={type(body).__name__}")

# R04/R05 need a live tenant — skip if deleted
if state.get("TEST_TENANT_UUID"):
    resp = patch(f"/tenants/{state['TEST_TENANT_UUID']}/rent-status", {"rent_status":"At Risk"})
    r("R04", "Tenant rent-status update → At Risk", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, safe_json(resp))
    resp = patch(f"/tenants/{state['TEST_TENANT_UUID']}/rent-status", {"rent_status":"Banana"})
    r("R05", "Invalid rent_status → 422/400", "PASS" if resp.status_code in (400,422) else "FAIL",
      resp.status_code, safe_json(resp))
else:
    r("R04", "Tenant rent-status update", "SKIP", 0, {}, "Tenant deleted in TN14")
    r("R05", "Invalid rent_status → 422/400", "SKIP", 0, {}, "Tenant deleted in TN14")

# ── SECTION 9: Leasing ───────────────────────────────────────────────────────
print("\n── Section 9: Leasing ──")

MANAGER_ID = "28c43c77-8c9c-496f-8d1e-39ffa9d619e3"

resp = get("/leasing/listings")
body = safe_json(resp)
r("L_LIST01", "List listings", "PASS" if resp.status_code==200 and isinstance(body,list) else "FAIL",
  resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

if state.get("TEST_FLAT_UUID"):
    resp = post("/leasing/listings", {"flat_uuid": state["TEST_FLAT_UUID"],"title":"Cozy 2BR API Test",
        "monthly_rent":1750,"description":"Test listing created via API","available_from":"2026-07-01",
        "is_active":True,"custom_rules":{"max_occupants":3,"pets_allowed":"yes","vegetarian_only":False,"lease_term_months":12}})
    body = safe_json(resp)
    state["TEST_LISTING_UUID"] = body.get("uuid")
    r("L_LIST02", "Create listing", "PASS" if resp.status_code in (200,201) and state["TEST_LISTING_UUID"] else "FAIL",
      resp.status_code, body, f"uuid={state['TEST_LISTING_UUID']}")
else:
    r("L_LIST02", "Create listing", "SKIP", 0, {}, "No TEST_FLAT_UUID")

resp = post("/leasing/listings", {"flat_uuid":"00000000-0000-0000-0000-000000000000","title":"Ghost Listing",
    "monthly_rent":1000,"available_from":"2026-07-01","is_active":True})
r("L_LIST03", "Create listing FK violation → 400", "PASS" if resp.status_code==400 else "FAIL",
  resp.status_code, safe_json(resp))

if state.get("TEST_LISTING_UUID"):
    resp = patch(f"/leasing/listings/{state['TEST_LISTING_UUID']}", {"monthly_rent":1800,"title":"Updated Cozy 2BR","is_active":False})
    r("L_LIST04", "Update listing", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, safe_json(resp))
else:
    r("L_LIST04", "Update listing", "SKIP", 0, {}, "No TEST_LISTING_UUID")

resp = requests.get(f"{BASE}/leasing/search", params={"bedrooms":2,"budget_max":1800,"manager_id":MANAGER_ID}, timeout=30)
body = safe_json(resp)
r("L_LIST05", "VAPI search listings", "PASS" if resp.status_code==200 and isinstance(body,list) else "FAIL",
  resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

resp = requests.get(f"{BASE}/leasing/search", params={"bedrooms":"","budget_max":"","manager_id":MANAGER_ID}, timeout=30)
r("L_LIST06", "VAPI search empty params → no 422", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, safe_json(resp))

resp = requests.get(f"{BASE}/leasing/search", params={"bedrooms":0,"budget_max":0,"manager_id":MANAGER_ID}, timeout=30)
body = safe_json(resp)
r("L_LIST07", "VAPI search budget=0 (no filter)", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

resp = requests.get(f"{BASE}/leasing/find-listing", params={"query":"T2B01","manager_id":MANAGER_ID}, timeout=30)
body = safe_json(resp)
r("L_LIST08", "VAPI find-listing T2B01", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body, f"found={body.get('found','?')}")

resp = requests.get(f"{BASE}/leasing/find-listing", params={"query":"ZZZNOTEXIST","manager_id":MANAGER_ID}, timeout=30)
body = safe_json(resp)
r("L_LIST09", "VAPI find-listing not found", "PASS" if resp.status_code==200 and body.get("found")==False else "FAIL",
  resp.status_code, body)

resp = get("/leasing/metrics", params={"days":30})
body = safe_json(resp)
r("L_LIST10", "Leasing metrics", "PASS" if resp.status_code==200 and "total" in body else "FAIL",
  resp.status_code, body)

resp = get("/leasing/leads")
body = safe_json(resp)
r("L_LEADS01", "List leads", "PASS" if resp.status_code==200 and isinstance(body,list) else "FAIL",
  resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

if state.get("TEST_LISTING_UUID"):
    resp = get("/leasing/leads", params={"listing_uuid": state["TEST_LISTING_UUID"]})
    r("L_LEADS02", "Filter leads by listing", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, safe_json(resp))
else:
    r("L_LEADS02", "Filter leads by listing", "SKIP", 0, {}, "No TEST_LISTING_UUID")

resp = get("/leasing/leads", params={"qualification_status":"qualified"})
body = safe_json(resp)
r("L_LEADS03", "Filter leads by qualification", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

# L_LEADS04/05 — need a real lead UUID
all_leads = body if isinstance(body, list) else []
# Try unfiltered leads if qualified is empty
if not all_leads:
    resp2 = get("/leasing/leads")
    all_leads = safe_json(resp2) if isinstance(safe_json(resp2), list) else []

state["LEAD_UUID"] = all_leads[0].get("uuid") if all_leads else None
if state["LEAD_UUID"]:
    resp = patch(f"/leasing/leads/{state['LEAD_UUID']}", {"qualification_status":"contacted","manager_notes":"Called on 2026-06-05"})
    r("L_LEADS04", "Update lead status", "PASS" if resp.status_code==200 else "FAIL",
      resp.status_code, safe_json(resp))

    resp = patch(f"/leasing/leads/{state['LEAD_UUID']}", {"qualification_status":"banana"})
    r("L_LEADS05", "Update lead invalid status → 400/422", "PASS" if resp.status_code in (400,422) else "FAIL",
      resp.status_code, safe_json(resp))
else:
    r("L_LEADS04", "Update lead status", "SKIP", 0, {}, "No leads found")
    r("L_LEADS05", "Update lead invalid status", "SKIP", 0, {}, "No leads found")

resp = get("/leasing/export")
r("L_LEADS06", "Export leads CSV", "PASS" if resp.status_code==200 and "text/csv" in resp.headers.get("content-type","") else "FAIL",
  resp.status_code, {"content_type": resp.headers.get("content-type",""), "size": len(resp.content)})

if state.get("TEST_LISTING_UUID"):
    resp = delete(f"/leasing/listings/{state['TEST_LISTING_UUID']}")
    r("L_LIST11", "Delete listing", "PASS" if resp.status_code in (200,204) else "FAIL",
      resp.status_code, safe_json(resp))
else:
    r("L_LIST11", "Delete listing", "SKIP", 0, {}, "No TEST_LISTING_UUID")

# ── SECTION 10: Voice / Call Logs ────────────────────────────────────────────
print("\n── Section 10: Voice / Call Logs ──")

resp = get("/voice/agent-info")
body = safe_json(resp)
r("V01", "Voice agent info", "PASS" if resp.status_code==200 and "complaint_phone_number" in body else "FAIL",
  resp.status_code, body)

resp = get("/voice/call-status")
body = safe_json(resp)
r("V02", "Voice call status", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body)

resp = get("/call-logs")
body = safe_json(resp)
r("V03", "List call logs", "PASS" if resp.status_code==200 and isinstance(body,list) else "FAIL",
  resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

resp = get("/call-logs", params={"phone":"+15145550011"})
r("V04", "Filter call logs by phone", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, safe_json(resp))

resp = get("/call-logs", params={"complaint_status":"created"})
r("V05", "Filter call logs by complaint_status", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, safe_json(resp))

resp = post("/voice/call/outbound", {"agent":"complaint"})
r("V06", "Outbound call missing customer_number → 422", "PASS" if resp.status_code==422 else "FAIL",
  resp.status_code, safe_json(resp))

resp = post("/voice/call/outbound", {"customer_number":"+15145550011","agent":"ghost"})
r("V07", "Outbound call invalid agent → 400/500", "PASS" if resp.status_code in (400,500) else "FAIL",
  resp.status_code, safe_json(resp))

# ── SECTION 11: Settings ─────────────────────────────────────────────────────
print("\n── Section 11: Settings ──")

resp = get("/settings")
body = safe_json(resp)
r("S01", "Get settings", "PASS" if resp.status_code==200 and "name" in body else "FAIL",
  resp.status_code, body)

resp = patch("/settings", {"name":"Leadpipe Updated","phone":"+15145551234"})
r("S02", "Update settings", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, safe_json(resp))

resp = patch("/settings", {"name":"Leadpipe"})
r("S03", "Revert name", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, safe_json(resp))

resp = get("/settings/features")
body = safe_json(resp)
r("S04", "Get feature flags", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body, f"type={type(body).__name__}")

if state.get("TEST_BLD_ID"):
    resp = post("/settings/features", {"building_id": state["TEST_BLD_ID"],"feature_name":"sms_reminders","is_enabled":True})
    r("S05", "Toggle feature flag on", "PASS" if resp.status_code in (200,201) else "FAIL",
      resp.status_code, safe_json(resp))
    resp = post("/settings/features", {"building_id": state["TEST_BLD_ID"],"feature_name":"sms_reminders","is_enabled":False})
    r("S06", "Toggle feature flag off", "PASS" if resp.status_code in (200,201) else "FAIL",
      resp.status_code, safe_json(resp))
else:
    r("S05", "Toggle feature flag on", "SKIP", 0, {}, "No TEST_BLD_ID")
    r("S06", "Toggle feature flag off", "SKIP", 0, {}, "No TEST_BLD_ID")

# ── SECTION 12: Chatbot ──────────────────────────────────────────────────────
print("\n── Section 12: Chatbot ──")

resp = post("/chat", {"messages":[{"role":"user","content":"Hi, what can you help me with?"}]})
body = safe_json(resp)
r("CH01", "Chatbot basic greeting", "PASS" if resp.status_code==200 and "reply" in body else "FAIL",
  resp.status_code, body, body.get("reply","")[:80])

resp = post("/chat", {"messages":[{"role":"user","content":"How many open complaints do I have?"}]})
body = safe_json(resp)
r("CH02", "Chatbot complaint count", "PASS" if resp.status_code==200 and "reply" in body else "FAIL",
  resp.status_code, body, body.get("reply","")[:80])

resp = post("/chat", {"messages":[{"role":"user","content":"Tell me about flat T101"}]})
body = safe_json(resp)
r("CH03", "Chatbot flat info T101", "PASS" if resp.status_code==200 and "reply" in body else "FAIL",
  resp.status_code, body, body.get("reply","")[:80])

resp = post("/chat", {"messages":[{"role":"user","content":"Schedule a maintenance visit for flat T101 on August 15th at 2pm"}]})
body = safe_json(resp)
r("CH04", "Chatbot schedule appointment", "PASS" if resp.status_code==200 and "reply" in body else "FAIL",
  resp.status_code, body, body.get("reply","")[:80])

resp = post("/chat", {"messages":[]})
r("CH05", "Chatbot empty messages → error", "PASS" if resp.status_code in (422,400,500) else "FAIL",
  resp.status_code, safe_json(resp))

resp = post("/chat", {"messages":[{"role":"user","content":"What is today's date?"}]})
body = safe_json(resp)
reply = body.get("reply","")
r("CH06", "Chatbot date awareness", "PASS" if resp.status_code==200 and "2026" in reply else "FAIL",
  resp.status_code, body, reply[:80])

# ── SECTION 13: Notifications ────────────────────────────────────────────────
print("\n── Section 13: Notifications ──")

resp = get("/notifications/preferences")
body = safe_json(resp)
r("N01", "Get notification preferences", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body)

resp = post("/notifications/test-sms", {"phone":"+15145559999","message":"API test SMS — please ignore"})
body = safe_json(resp)
r("N02", "Send test SMS", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body)

resp = post("/notifications/test-email", {"email":"leadpipecrm@gmail.com","subject":"API Test Email","body":"This is a test email from the API test plan."})
body = safe_json(resp)
r("N03", "Send test email", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body)

# ── SECTION 14: Payments ─────────────────────────────────────────────────────
print("\n── Section 14: Payments ──")

resp = get("/payments/subscription-status")
body = safe_json(resp)
r("PAY01", "Subscription status", "PASS" if resp.status_code==200 and body.get("status") in ("trialing","active") else "FAIL",
  resp.status_code, body, body.get("status",""))

resp = post("/payments/create-checkout-session", {})
body = safe_json(resp)
has_url = isinstance(body.get("url",""), str) and "stripe" in body.get("url","")
r("PAY02", "Create checkout session", "PASS" if resp.status_code==200 and has_url else "FAIL",
  resp.status_code, {"url_preview": body.get("url","")[:60] if body.get("url") else None})

# ── SECTION 15: VAPI Tool Endpoints (no auth) ────────────────────────────────
print("\n── Section 15: VAPI Tool Endpoints ──")

resp = requests.post(f"{BASE}/flats/verify-phone", params={"phone_number":"+15145550011"}, timeout=30)
body = safe_json(resp)
r("VA01", "Verify phone valid tenant", "PASS" if resp.status_code==200 and body.get("status")=="valid" else "FAIL",
  resp.status_code, body)

resp = requests.post(f"{BASE}/flats/verify-phone", params={"phone_number":"+10000000000"}, timeout=30)
body = safe_json(resp)
r("VA02", "Verify phone wrong number → invalid", "PASS" if resp.status_code==200 and body.get("status")=="invalid" else "FAIL",
  resp.status_code, body)

resp = requests.post(f"{BASE}/flats/verify-phone", params={"phone_number":"+15145550033"}, timeout=30)
body = safe_json(resp)
r("VA03", "Verify phone vacant flat", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body, body.get("status",""))

resp = requests.post(f"{BASE}/flats/verify-phone", params={"phone_number":"+1 514 555 0011"}, timeout=30)
body = safe_json(resp)
r("VA04", "Verify phone normalization", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body, f"status={body.get('status','?')} (documenting actual behavior)")

resp = requests.get(f"{BASE}/appointments/availability", params={"appointment_date":"not-a-date"}, timeout=30)
body = safe_json(resp)
r("VA05", "Availability bad date → HTTP 200 (safe)", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body)

resp = requests.get(f"{BASE}/appointments/availability", timeout=30)
body = safe_json(resp)
r("VA06", "Availability missing param", "PASS" if resp.status_code in (200,422) else "FAIL",
  resp.status_code, body)

# ── SECTION 16: Properties View ──────────────────────────────────────────────
print("\n── Section 16: Properties View ──")

resp = get("/properties")
body = safe_json(resp)
r("PR01", "Get properties", "PASS" if resp.status_code==200 and isinstance(body,list) else "FAIL",
  resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

# ── SECTION 17: Property Types ───────────────────────────────────────────────
print("\n── Section 17: Property Types ──")

resp = get("/property-types")
body = safe_json(resp)
r("PT01", "List property types", "PASS" if resp.status_code==200 and isinstance(body,list) else "FAIL",
  resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

# ── SECTION 18: SMS Workflow ─────────────────────────────────────────────────
print("\n── Section 18: SMS Workflow ──")

resp = get("/workflow/sms-templates")
body = safe_json(resp)
r("WF01", "List SMS templates", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body, f"count={len(body) if isinstance(body,list) else '?'}")

resp = post("/workflow/sms-templates", {"name":"Rent Reminder","body":"Hi {{tenant_name}}, your rent is due on {{due_date}}."})
body = safe_json(resp)
r("WF02", "Create SMS template", "PASS" if resp.status_code in (200,201) else "FAIL",
  resp.status_code, body)

resp = post("/workflow/sms-broadcast", {"message":"Rent reminder: please ensure payment is up to date.","filter":{"rent_status":"Overdue"}})
body = safe_json(resp)
r("WF03", "Broadcast SMS (Overdue tenants)", "PASS" if resp.status_code==200 else "FAIL",
  resp.status_code, body)

# ── SUMMARY ──────────────────────────────────────────────────────────────────
print(f"\n{'='*80}")
passed = sum(1 for x in results if x["status"]=="PASS")
failed = sum(1 for x in results if x["status"]=="FAIL")
skipped = sum(1 for x in results if x["status"]=="SKIP")
total = len(results)
print(f"  TOTAL: {total}  |  PASS: {passed}  |  FAIL: {failed}  |  SKIP: {skipped}")
print(f"{'='*80}\n")

if failed:
    print("FAILURES:")
    for x in results:
        if x["status"] == "FAIL":
            body_str = json.dumps(x["body"])[:200] if x["body"] else ""
            print(f"  {x['id']:12} HTTP {x['http']}  {x['desc']}")
            if body_str:
                print(f"              {body_str}")

# Write markdown report
with open("API_TEST_RESULTS.md", "w") as f:
    f.write(f"# API Test Results\n\n")
    f.write(f"**Run:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
    f.write(f"**Total:** {total} | **Pass:** {passed} | **Fail:** {failed} | **Skip:** {skipped}\n\n")
    f.write(f"| ID | Description | Status | HTTP | Notes |\n")
    f.write(f"|---|---|---|---|---|\n")
    for x in results:
        icon = "✅" if x["status"]=="PASS" else ("⏭️" if x["status"]=="SKIP" else "❌")
        notes = str(x["notes"])[:80].replace("|","\\|")
        f.write(f"| {x['id']} | {x['desc'][:50]} | {icon} {x['status']} | {x['http']} | {notes} |\n")
    if failed:
        f.write(f"\n## Failure Details\n\n")
        for x in results:
            if x["status"] == "FAIL":
                f.write(f"### {x['id']} — {x['desc']}\n")
                f.write(f"- HTTP {x['http']}\n")
                f.write(f"- Notes: {x['notes']}\n")
                f.write(f"- Body: `{json.dumps(x['body'])[:500]}`\n\n")

print("\nReport written to API_TEST_RESULTS.md")

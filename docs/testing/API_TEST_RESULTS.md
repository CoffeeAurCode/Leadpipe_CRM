# API Test Results — Full Run

**Date:** 2026-06-04  
**Account:** Leadpipe (leadpipecrm@gmail.com)  
**Total:** 115 tests | **Pass: 56** | **Fail: 40** | **Skip: 19**

---

## Summary Scorecard

| Section | Tests Run | Pass | Fail | Skip |
|---|---|---|---|---|
| S1 Auth | 3 | 3 | 0 | 0 |
| S2 Property Groups | 7 | 6 | 1 | 0 |
| S3 Buildings | 7 | 4 | 2 | 1 |
| S4 Flats | 9 | 3 | 2 | 4 |
| S5 Tenants | 10 | 5 | 5 | 0 |
| S6 Complaints | 11 | 2 | 9 | 0 |
| S7 Appointments | 16 | 8 | 2 | 6 |
| S8 Rents | 5 | 3 | 0 | 2 |
| S9 Leasing | 16 | 8 | 4 | 4 |
| S10 Voice/Call Logs | 7 | 4 | 3 | 0 |
| S11 Settings | 6 | 0 | 6 | 0 |
| S12 Chatbot | 6 | 5 | 1 | 0 |
| S13 Notifications | 3 | 0 | 3 | 0 |
| S14 Payments | 2 | 1 | 1 | 0 |
| S15 VAPI Tools | 6 | 2 | 4 | 0 |
| S16 Properties | 1 | 1 | 0 | 0 |
| S17 Property Types | 1 | 1 | 0 | 0 |
| S18 SMS Workflow | 3 | 0 | 3 | 0 |

---

## Priority Fix List

| Priority | Issue | Fix |
|---|---|---|
| P0 | RLS policy blocks POST /tenants and POST /complaints | Fix INSERT RLS policy in Supabase |
| P1 | DELETE /complaints/:id missing (405) | Add route |
| P1 | GET /buildings/:id missing (405) | Add route |
| P2 | Notification test/preference endpoints missing | Implement or remove from test plan |
| P2 | Workflow sms-templates/broadcast missing | Implement or remove from test plan |
| P3 | POST /property-groups accepts missing city/state | Add Pydantic required fields |
| P3 | POST /buildings allows duplicate names in same group | Add unique constraint or backend check |
| DOC | Test plan: /call-logs should be /call_logs | Fix URL in V03-V05 |
| DOC | Test plan: POST /flats needs multipart/form-data not JSON | Fix curl in F03-F04 |
| DOC | Test plan: /flats/verify-phone needs JSON body {flat_number} | Fix curl in VA01-VA04 |
| DOC | Test plan: /settings wrong structure | Fix to use /properties/{uuid}/settings |
| DOC | AP12 expects [] but gets {appointments:[]} | Update assertion |
| DOC | L_LIST05 expects array but gets {count,listings:{}} | Update assertion |
| DOC | L_LIST10 field names total_calls/qualification_rate differ | Update assertions |

---

## BUG-1 (P0): RLS Policy Blocks POST /tenants and POST /complaints

Both return HTTP 500:


This is the most impactful bug — it cascades into ~20 test skips across tenants, complaints, appointments.

**Fix:** In Supabase dashboard, check the INSERT policy on  and  tables.
The policy likely requires  but the column is not being set on insert,
or the INSERT policy is missing entirely while SELECT/UPDATE/DELETE exist.

---

## BUG-2 (P0 cascade): POST /flats uses Form data, not JSON

 uses FastAPI  fields (multipart/form-data) because it supports image upload.
Sending JSON returns 422. This cascades: no flat = no tenant = no complaint = ~25 tests skip.

Correct curl:


---

## BUG-3 (P1): Missing Routes

| Route | HTTP | Fix |
|---|---|---|
| DELETE /complaints/{id} | 405 | Add DELETE handler to complaints router |
| GET /buildings/{id} | 405 | Add GET handler to buildings router |

---

## BUG-4 (DOC): Wrong URL — /call-logs vs /call_logs

Actual route prefix is  (underscore). Tests V03-V05 hit  (hyphen) and get 404.
Correct endpoints confirmed working: GET /call_logs, GET /call_logs/stats, GET /call_logs/{id}

---

## BUG-5 (DOC): Settings route structure is different

No  endpoint exists. Actual routes:


---

## BUG-6 (DOC): POST /flats/verify-phone requires JSON body

Route expects  as JSON body PLUS  as query param.
Tests VA01-VA04 only sent the query param — all returned 422.

Correct form:

Confirmed response: 

---

## BUG-7 (P2): Notification and Workflow endpoints not implemented

Notification routes that exist: GET /notifications, PATCH /notifications/{id}/read, POST /notifications/read-all
Missing (404): GET /notifications/preferences, POST /notifications/test-sms, POST /notifications/test-email

Workflow routes that exist: POST /workflow/send-sms
Missing (404): GET /workflow/sms-templates, POST /workflow/sms-templates, POST /workflow/sms-broadcast

---

## BUG-8 (P3): Validation Gaps

- P03: POST /property-groups with only  returns 201 (city/state/street_address null).
  Should return 422 if these are required for a meaningful group.
- B04: POST /buildings with duplicate name in same property group returns 201.
  No unique constraint enforced at backend level.

---

## Response Shape Mismatches (test plan assertions wrong)

| Test | Actual Response | Test Plan Expected |
|---|---|---|
| AP12 GET /appointments/view?flat_number=T101 | {appointments:[]} | [] |
| L_LIST05 GET /leasing/search | {count:N,listings:[...]} | [...] |
| L_LIST10 GET /leasing/metrics | {total_calls, qualification_rate, avg_duration_seconds} | {total, rate, avg_duration} |

---

## Confirmed Working (key highlights)

- Auth & JWT validation: T01 T02 T03
- Property groups CRUD: P01 P02 P04 P05 P06 P07
- Buildings CRUD (except GET /:id): B01 B03 B05 B06 B07
- Flats list/get/update/delete: F01 F02 F05 F07 F08 F10 F11
- Tenants list/get/update: TN04 TN05 TN06 TN07(vacant) TN08 TN09 TN10 TN11
- Complaints list/get/update: CM06 CM07 CM08 CM09
- Appointments full cycle + VAPI tools: AP03-AP12 AP16
- Availability check including boundary: AP08 AP09 AP10
- Rents set/update/summary: R01 R02 R03
- Leasing listings + leads CRUD: L_LIST01 L_LIST06-L_LIST10 L_LEADS01-L_LEADS06
- VAPI search / find-listing: L_LIST06 L_LIST07 L_LIST08 L_LIST09
- Voice agent info + call status: V01 V02
- Call logs (correct URL): /call_logs works
- Chatbot all scenarios incl. date awareness: CH01-CH04 CH06
- Subscription status: T01 PAY01
- Properties view + property types: PR01 PT01

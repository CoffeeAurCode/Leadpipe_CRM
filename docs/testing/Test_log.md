## Part 5 — Second Sweep: Post-Fix Regression (Manual)

INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
============================================================
[LEASE LEAD WEBHOOK] Incoming payload
  message.type:     tool-calls
  call.id:          019e5354-4789-7331-a87d-f90a0f276add
  call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
  call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
  customer.number:  +919998064026
  [submit_lease_lead args]
    bedrooms: 2
    occupants: 0
    budget_max: 30000
    caller_name: test person 1
    listing_uuid: 34e98d28-8bd7-4480-9ca3-a013e13a2319
    floor_preference: 
    move_in_timeline: Within the next month
    qualifying_answers: {}
    disqualifying_reason: 
    qualification_status: qualified
    interested_listing_ids: ['34e98d28-8bd7-4480-9ca3-a013e13a2319']
  [pg resolution] path=listing_uuid property_group_id=31ed35ee-977a-4416-8fad-b3f25e12fc43
  [manager resolution] manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3
  [SAVED] phone=+919998064026 status=qualified property_group_id=31ed35ee-977a-4416-8fad-b3f25e12fc43
  [NOTIFICATION] Qualified lead notification created for manager 28c43c77-8c9c-496f-8d1e-39ffa9d619e3
============================================================
INFO:     35.93.49.56:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK

### Sweep 2-B — Re-run Scenario D: Verify pet rule read and correct budget capture
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
============================================================
[LEASE LEAD WEBHOOK] Incoming payload
  message.type:     tool-calls
  call.id:          019e5357-0219-7dd9-a6e2-a484181a177e
  call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
  call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
  customer.number:  +919998064026
  [submit_lease_lead args]
    bedrooms: 2
    occupants: 1
    budget_max: 45000
    caller_name: Despa Sanju
    listing_uuid: b5f4efd5-0e61-483c-84bf-56da7c9250f8
    floor_preference: 
    move_in_timeline: next week
    qualifying_answers: {}
    disqualifying_reason: 
    qualification_status: qualified
    interested_listing_ids: ['b5f4efd5-0e61-483c-84bf-56da7c9250f8']
  [pg resolution] path=listing_uuid property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
  [manager resolution] manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3
  [SAVED] phone=+919998064026 status=qualified property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
  [NOTIFICATION] Qualified lead notification created for manager 28c43c77-8c9c-496f-8d1e-39ffa9d619e3
============================================================
INFO:     54.186.200.145:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK
### Sweep 2-C — Re-run Scenario E: Verify E501 is found and income rule applied
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
============================================================
[LEASE LEAD WEBHOOK] Incoming payload
  message.type:     tool-calls
  call.id:          019e535b-d92c-7dd9-a6ff-e1703d890533
  call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
  call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
  customer.number:  +919998064026
  [submit_lease_lead args]
    bedrooms: 3
    occupants: 0
    budget_max: 200000
    caller_name: Person 3
    listing_uuid: 
    floor_preference: 5th floor only
    move_in_timeline: 
    qualifying_answers: {}
    disqualifying_reason: No 3 bedroom units available on 5th floor within budget
    qualification_status: unmatched
    interested_listing_ids: []
  [WARN] Could not resolve property_group_id for assistant=2dba3a50-6862-400c-861a-bfc0a45d4a95 phone_number_id=969c6812-b520-468e-8f65-5fb8ca4ee240
  [pg resolution] path=unresolved property_group_id=None
  [manager resolution] manager_id=None
  [SAVED] phone=+919998064026 status=unmatched property_group_id=None
============================================================
INFO:     44.255.29.95:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK

### Sweep 2-E — Duplicate lead suppression
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
============================================================
[LEASE LEAD WEBHOOK] Incoming payload
  message.type:     tool-calls
  call.id:          019e535e-a8d2-7dd9-a711-3d5095e93d0f
  call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
  call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
  customer.number:  +919998064026
  [submit_lease_lead args]
    bedrooms: 2
    occupants: 0
    budget_max: 60
    caller_name: person 4
    listing_uuid: 
    floor_preference: high floor
    move_in_timeline: this month
    qualifying_answers: {}
    disqualifying_reason: 
    qualification_status: unmatched
    interested_listing_ids: []
  [WARN] Could not resolve property_group_id for assistant=2dba3a50-6862-400c-861a-bfc0a45d4a95 phone_number_id=969c6812-b520-468e-8f65-5fb8ca4ee240
  [pg resolution] path=unresolved property_group_id=None
  [manager resolution] manager_id=None
  [SAVED] phone=+919998064026 status=unmatched property_group_id=None
============================================================
INFO:     54.201.109.19:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK
### Sweep 2-F — Scenario F: Wrong bedroom count (first run)
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
============================================================
[LEASE LEAD WEBHOOK] Incoming payload
  message.type:     tool-calls
  call.id:          019e5365-9366-7885-9396-977215ba1081
  call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
  call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
  customer.number:  +919998064026
  [submit_lease_lead args]
    bedrooms: 4
    occupants: 0
    budget_max: 300000
    caller_name: Jeff Person 5
    listing_uuid: 
    floor_preference: 
    move_in_timeline: This month
    qualifying_answers: {}
    disqualifying_reason: 
    qualification_status: unmatched
    interested_listing_ids: []
  [WARN] Could not resolve property_group_id for assistant=2dba3a50-6862-400c-861a-bfc0a45d4a95 phone_number_id=969c6812-b520-468e-8f65-5fb8ca4ee240
  [pg resolution] path=unresolved property_group_id=None
  [manager resolution] manager_id=None
  [SAVED] phone=+919998064026 status=unmatched property_group_id=None
============================================================
INFO:     34.213.71.234:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK
### Sweep 2-G — Scenario G: Find listing by address query (first run)
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
============================================================
[LEASE LEAD WEBHOOK] Incoming payload
  message.type:     tool-calls
  call.id:          019e53a5-c8ed-7dd9-a8dd-23ab0b8c48a5
  call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
  call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
  customer.number:  +919998064026
  [submit_lease_lead args]
    bedrooms: 3
    occupants: 1
    budget_max: 70000
    caller_name: Desmos on 6
    listing_uuid: b9f94428-4efd-44ed-bc5a-ad740cb86c4b
    floor_preference: 
    move_in_timeline: by the end of this month
    qualifying_answers: {"stable_income":"yes","occupants":"1","12_month_lease":"yes"}
    disqualifying_reason: 
    qualification_status: qualified
    interested_listing_ids: ['b9f94428-4efd-44ed-bc5a-ad740cb86c4b']
  [pg resolution] path=listing_uuid property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
  [manager resolution] manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3
  [SAVED] phone=+919998064026 status=qualified property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
  [NOTIFICATION] Qualified lead notification created for manager 28c43c77-8c9c-496f-8d1e-39ffa9d619e3
============================================================
INFO:     35.93.49.56:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK
### Sweep 2-H — Scenario H: Caller hangs up — no lead inserted (first run)
  49.43.26.17:0 - "POST /voice/call/outbound HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
### Sweep 2-I — Scenario I: Budget exactly at rent price — boundary test (first run)
 49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     54.213.112.50:0 - "GET /leasing/search?bedrooms=2&budget_max=38000 HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /appointments?start_date=2026-02-22&end_date=2026-06-22 HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
============================================================
[LEASE LEAD WEBHOOK] Incoming payload
  message.type:     tool-calls
  call.id:          019e53ad-1c27-7ffa-aae2-b9cf305d8460
  call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
  call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
  customer.number:  +919998064026
  [submit_lease_lead args]
    bedrooms: 2
    occupants: 1
    budget_max: 38000
    caller_name: test person I
    listing_uuid: b8f3aed7-fe82-49ce-8fed-91180f2fd19e
    floor_preference: 
    move_in_timeline: June
    qualifying_answers: {"stable_income":"yes","occupants":"1","12_month_lease":"yes"}
    disqualifying_reason: 
    qualification_status: qualified
    interested_listing_ids: ['b8f3aed7-fe82-49ce-8fed-91180f2fd19e']
  [pg resolution] path=listing_uuid property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
  [manager resolution] manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3
  [SAVED] phone=+919998064026 status=qualified property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
  [NOTIFICATION] Qualified lead notification created for manager 28c43c77-8c9c-496f-8d1e-39ffa9d619e3
============================================================
INFO:     54.213.112.50:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
### Sweep 2-I — Scenario I: Budget exactly at rent price — boundary test (first run)
  49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     54.213.112.50:0 - "GET /leasing/search?bedrooms=2&budget_max=38000 HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /appointments?start_date=2026-02-22&end_date=2026-06-22 HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
============================================================
[LEASE LEAD WEBHOOK] Incoming payload
  message.type:     tool-calls
  call.id:          019e53ad-1c27-7ffa-aae2-b9cf305d8460
  call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
  call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
  customer.number:  +919998064026
  [submit_lease_lead args]
    bedrooms: 2
    occupants: 1
    budget_max: 38000
    caller_name: test person I
    listing_uuid: b8f3aed7-fe82-49ce-8fed-91180f2fd19e
    floor_preference: 
    move_in_timeline: June
    qualifying_answers: {"stable_income":"yes","occupants":"1","12_month_lease":"yes"}
    disqualifying_reason: 
    qualification_status: qualified
    interested_listing_ids: ['b8f3aed7-fe82-49ce-8fed-91180f2fd19e']
  [pg resolution] path=listing_uuid property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
  [manager resolution] manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3
  [SAVED] phone=+919998064026 status=qualified property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
  [NOTIFICATION] Qualified lead notification created for manager 28c43c77-8c9c-496f-8d1e-39ffa9d619e3
============================================================
INFO:     54.213.112.50:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
### Sweep 2-J — Scenario J: Caller pivots to 1BHK after initial decline (first run)
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     54.186.200.145:0 - "GET /leasing/search?bedrooms=1&budget_max=10000 HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
============================================================
[LEASE LEAD WEBHOOK] Incoming payload
  message.type:     tool-calls
  call.id:          019e53b2-190e-7ff9-a6f4-40c70d0581ca
  call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
  call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
  customer.number:  +919998064026
  [submit_lease_lead args]
    bedrooms: 1
    occupants: 0
    budget_max: 10000
    caller_name: Despa Sanjay
    listing_uuid: 
    floor_preference: 
    move_in_timeline: End of this month
    qualifying_answers: {}
    disqualifying_reason: 
    qualification_status: unmatched
    interested_listing_ids: []
  [WARN] Could not resolve property_group_id for assistant=2dba3a50-6862-400c-861a-bfc0a45d4a95 phone_number_id=969c6812-b520-468e-8f65-5fb8ca4ee240
  [pg resolution] path=unresolved property_group_id=None
  [manager resolution] manager_id=None
  [SAVED] phone=+919998064026 status=unmatched property_group_id=None
============================================================
INFO:     54.186.200.145:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
### Sweep 2 — Post-run checklist
caller_name,bedrooms,budget_max,qualification_status,listing_uuid,property_group_id,call_id,created_at
Despa Sanjay,1,10000,unmatched,null,null,019e53b2-190e-7ff9-a6f4-40c70d0581ca,2026-05-23 07:18:50.856198+00
test person I,2,38000,qualified,b8f3aed7-fe82-49ce-8fed-91180f2fd19e,aeb9d575-42e2-439f-ad81-8e99ae6900ed,019e53ad-1c27-7ffa-aae2-b9cf305d8460,2026-05-23 07:13:52.231128+00
Desmos on 6,3,70000,qualified,b9f94428-4efd-44ed-bc5a-ad740cb86c4b,aeb9d575-42e2-439f-ad81-8e99ae6900ed,019e53a5-c8ed-7dd9-a8dd-23ab0b8c48a5,2026-05-23 07:07:12.622527+00
Jeff Person 5,4,300000,unmatched,null,null,019e5365-9366-7885-9396-977215ba1081,2026-05-23 05:56:16.651424+00
person 4,2,60,unmatched,null,null,019e535e-a8d2-7dd9-a711-3d5095e93d0f,2026-05-23 05:47:52.990389+00
Person 3,3,200000,unmatched,null,null,019e535b-d92c-7dd9-a6ff-e1703d890533,2026-05-23 05:44:47.981683+00
Despa Sanju,2,45000,qualified,b5f4efd5-0e61-483c-84bf-56da7c9250f8,aeb9d575-42e2-439f-ad81-8e99ae6900ed,019e5357-0219-7dd9-a6e2-a484181a177e,2026-05-23 05:39:29.434902+00
test person 1,2,30000,qualified,34e98d28-8bd7-4480-9ca3-a013e13a2319,31ed35ee-977a-4416-8fad-b3f25e12fc43,019e5354-4789-7331-a87d-f90a0f276add,2026-05-23 05:36:15.288236+00

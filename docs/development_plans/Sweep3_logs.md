## Sweep 3-A — Re-test: Budget too low (was Sweep 2-A FAIL)

INFO:     16.147.254.197:0 - "GET /leasing/search?bedrooms=2&budget_max=30000&manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3 HTTP/1.1" 200 OK
Menu
============================================================
[LEASE LEAD WEBHOOK] Incoming payload
  message.type:     tool-calls
  call.id:          019e54d4-885f-7000-a3c1-badd95c61e17
  call.assistantId: c76a69ea-103d-4a24-b542-adda79957294
  call.phoneNumberId: 857191a6-81ec-4fe1-bc45-2e955ec17542
  customer.number:  +919998064026
  [submit_lease_lead args]
    bedrooms: 2
    occupants: 0
    budget_max: 30000
    caller_name: Unknown
    listing_uuid: 
    floor_preference: 
    move_in_timeline: Next month
    qualifying_answers: {}
    disqualifying_reason: 
    qualification_status: unmatched
    interested_listing_ids: []
  [pg resolution] path=assistant_id→manager_vapi_config property_group_id=None
  [manager resolution] manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3
  [SAVED] phone=+919998064026 status=unmatched property_group_id=None
============================================================
INFO:     16.147.254.197:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK

## Sweep 3-B — Re-test: Penthouse / floor 5 (was Sweep 2-C FAIL)

INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
============================================================
[LEASE LEAD WEBHOOK] Incoming payload
  message.type:     tool-calls
  call.id:          019e54d8-b027-7000-91e6-7986366275de
  call.assistantId: c76a69ea-103d-4a24-b542-adda79957294
  call.phoneNumberId: 857191a6-81ec-4fe1-bc45-2e955ec17542
  customer.number:  +919998064026
  [submit_lease_lead args]
    bedrooms: 5
    occupants: 0
    budget_max: 200000
    caller_name: Desperson b
    listing_uuid: 
    floor_preference: fifth floor
    move_in_timeline: 
    qualifying_answers: {}
    disqualifying_reason: 
    qualification_status: unmatched
    interested_listing_ids: []
  [pg resolution] path=assistant_id→manager_vapi_config property_group_id=None
  [manager resolution] manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3
  [SAVED] phone=+919998064026 status=unmatched property_group_id=None
============================================================
INFO:     52.12.85.69:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK
## Sweep 3-C — Outbound Complaint Call (NEW — was blocked by bug)
 49.43.26.17:0 - "OPTIONS /property-groups HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "OPTIONS /buildings HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /property-groups HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /buildings HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "OPTIONS /properties HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /properties HTTP/1.1" 500 Internal Server Error
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/uvicorn/protocols/http/h11_impl.py", line 410, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        self.scope, self.receive, self.send
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/applications.py", line 1135, in __call__
    await super().__call__(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/applications.py", line 107, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py", line 186, in __call__
    raise exc
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/cors.py", line 93, in __call__
    await self.simple_response(scope, receive, send, request_headers=headers)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/cors.py", line 144, in simple_response
    await self.app(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
    await self.app(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/routing.py", line 716, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/routing.py", line 736, in app
    await route.handle(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/routing.py", line 290, in handle
    await self.app(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 115, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 101, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 377, in app
    content = await serialize_response(
              ^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<10 lines>...
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.13/site-packages/fastapi/routing.py", line 215, in serialize_response
    raise ResponseValidationError(
    ...<3 lines>...
    )
fastapi.exceptions.ResponseValidationError: 18 validation errors:
  {'type': 'int_type', 'loc': ('response', 15, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 16, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 17, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 18, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 19, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 20, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 21, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 22, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 23, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 24, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 25, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 26, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 27, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 28, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 29, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 30, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 31, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  {'type': 'int_type', 'loc': ('response', 32, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  File "/opt/render/project/src/backend/app/routes/properties.py", line 33, in get_all_properties
    GET /properties
INFO:     49.43.26.17:0 - "OPTIONS /buildings/7c3076c8-d3ad-4896-b1dc-8fa5a3e7507f/units HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /buildings/7c3076c8-d3ad-4896-b1dc-8fa5a3e7507f/units HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "OPTIONS /flats/e16c46c5-edfa-4c82-b703-4fde4a194b9c/details HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /flats/e16c46c5-edfa-4c82-b703-4fde4a194b9c/details HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "OPTIONS /units/113/settings HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /units/113/settings HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "OPTIONS /rents/e16c46c5-edfa-4c82-b703-4fde4a194b9c HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /rents/e16c46c5-edfa-4c82-b703-4fde4a194b9c HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "OPTIONS /flats/ae3fa7c6-8e5e-4915-8b21-433d3453fae6/details HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /flats/ae3fa7c6-8e5e-4915-8b21-433d3453fae6/details HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "OPTIONS /units/115/settings HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /units/115/settings HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "OPTIONS /rents/ae3fa7c6-8e5e-4915-8b21-433d3453fae6 HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /rents/ae3fa7c6-8e5e-4915-8b21-433d3453fae6 HTTP/1.1" 200 OK
[DEBUG] verify_phone: flat_number='1013' phone_number=' 919998064026'
[DEBUG] flat lookup '1013': found=False
INFO:     100.23.171.201:0 - "POST /flats/verify-phone?phone_number=+919998064026 HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "OPTIONS /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
## Sweep 3-D — Regression: Budget at boundary (was Sweep 2-I PASS)
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
============================================================
[LEASE LEAD WEBHOOK] Incoming payload
  message.type:     tool-calls
  call.id:          019e54dd-87dc-7dd9-a77d-6c870458589f
  call.assistantId: c76a69ea-103d-4a24-b542-adda79957294
  call.phoneNumberId: 857191a6-81ec-4fe1-bc45-2e955ec17542
  customer.number:  +919998064026
  [submit_lease_lead args]
    bedrooms: 2
    occupants: 1
    budget_max: 38000
    caller_name: Despa Sandee
    listing_uuid: b8f3aed7-fe82-49ce-8fed-91180f2fd19e
    floor_preference: 
    move_in_timeline: This month or next month, as soon as possible
    qualifying_answers: {"Do you have a stable source of income to cover the monthly rent?":"Yes","How many people will be living in the unit?":"1"}
    disqualifying_reason: 
    qualification_status: qualified
    interested_listing_ids: ['b8f3aed7-fe82-49ce-8fed-91180f2fd19e']
  [pg resolution] path=assistant_id→manager_vapi_config property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
  [manager resolution] manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3
  [SAVED] phone=+919998064026 status=qualified property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
  [NOTIFICATION] Qualified lead notification created for manager 28c43c77-8c9c-496f-8d1e-39ffa9d619e3
============================================================
INFO:     52.32.162.1:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK
## Sweep 3-E — Regression: Find by address (was Sweep 2-G PASS)
INFO:     49.43.26.17:0 - "POST /voice/call/outbound HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     34.220.153.40:0 - "GET /leasing/find-listing?query=third%20floor%20block&manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3 HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     34.220.153.40:0 - "GET /leasing/find-listing?query=Building%20C%20third%20floor&manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3 HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     34.220.153.40:0 - "GET /leasing/find-listing?query=C%20Block&manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3 HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     49.43.26.17:0 - "GET /voice/call-status HTTP/1.1" 200 OK
## Post-Run DB Verification Query
caller_name,bedrooms,budget_max,qualification_status,disqualifying_reason,listing_uuid,property_group_id,created_at
person E.,null,null,unmatched,No listing found matching the caller's description.,null,null,2026-05-23 12:48:44.951167+00
Despa Sandee,2,38000,qualified,,b8f3aed7-fe82-49ce-8fed-91180f2fd19e,aeb9d575-42e2-439f-ad81-8e99ae6900ed,2026-05-23 12:45:51.703641+00
Desperson b,5,200000,unmatched,,null,null,2026-05-23 12:40:32.458787+00
Unknown,2,30000,unmatched,,null,null,2026-05-23 12:36:02.792032+00
Despa Sanjay,1,10000,unmatched,,null,null,2026-05-23 07:18:50.856198+00
test person I,2,38000,qualified,,b8f3aed7-fe82-49ce-8fed-91180f2fd19e,aeb9d575-42e2-439f-ad81-8e99ae6900ed,2026-05-23 07:13:52.231128+00
Desmos on 6,3,70000,qualified,,b9f94428-4efd-44ed-bc5a-ad740cb86c4b,aeb9d575-42e2-439f-ad81-8e99ae6900ed,2026-05-23 07:07:12.622527+00
Jeff Person 5,4,300000,unmatched,,null,null,2026-05-23 05:56:16.651424+00
person 4,2,60,unmatched,,null,null,2026-05-23 05:47:52.990389+00
Person 3,3,200000,unmatched,No 3 bedroom units available on 5th floor within budget,null,null,2026-05-23 05:44:47.981683+00
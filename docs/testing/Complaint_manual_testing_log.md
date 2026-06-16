INFO:     152.58.179.47:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     34.219.238.108:0 - "GET /appointments/availability?appointment_date=2026-06-02T20:30:00 HTTP/1.1" 200 OK
================================================================================
VAPI FINAL EVENT: tool-calls
================================================================================
[CALL METADATA]
  call_id: 019e88cc-55d0-7000-b0de-c9c932acae03
  phone: +919123388359
[TRANSCRIPT]
  Hello? Can you talk in English?
Yes.
Yes. So my flat number is c my flat number is c 3 0 1.
As I nee...
[CONFIRMATION DETECTED]
  [OK] User confirmed complaint via submit_complaint
[COMPLAINT DATA]
  flat_number: C301
  category: water
  appointment_date: 2026-06-02T20:30:00
[VALIDATION]
  is_complete: True
[CALLLOG CREATED]
  ID: 56
  status: pending
[COMPLAINT CREATION]
  [BLOCKED] Voice calls feature is disabled for unit C301
  [X] Error: {'message': 'value too long for type character varying(20)', 'code': '22001', 'hint': None, 'details': None}
[AUTOMATION]
  call_id:           019e88cc-55d0-7000-b0de-c9c932acae03
  Complaint Created: No (exception)
  Triggering Notification: No
[FINAL STATE]
  CallLog: 56
  Complaint: None
  Status: failed
================================================================================
INFO:     34.219.238.108:0 - "POST /voice/webhook HTTP/1.1" 200 OK
INFO:     152.58.179.47:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     152.58.179.47:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     152.58.179.47:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     152.58.179.47:0 - "GET /notifications HTTP/1.1" 200 OK
INFO:     152.58.179.47:0 - "GET /voice/call-status HTTP/1.1" 200 OK
INFO:     152.58.179.47:0 - "OPTIONS /appointments?start_date=2026-03-04&end_date=2026-07-02 HTTP/1.1" 200 OK
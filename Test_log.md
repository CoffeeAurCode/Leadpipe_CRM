### Scenario A — Perfect Single Match (Happy Path)

2026-05-22T14:27:30.747724319Z ============================================================
2026-05-22T14:27:30.74773635Z [LEASE LEAD WEBHOOK] Incoming payload
2026-05-22T14:27:30.74773979Z   message.type:     tool-calls
2026-05-22T14:27:30.74774277Z   call.id:          019e5014-3e5c-7000-9a43-dc3cc8b84087
2026-05-22T14:27:30.74774583Z   call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
2026-05-22T14:27:30.74774893Z   call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
2026-05-22T14:27:30.747769281Z   customer.number:  +919998064026
2026-05-22T14:27:30.747775131Z   [submit_lease_lead args]
2026-05-22T14:27:30.747778101Z     bedrooms: 2
2026-05-22T14:27:30.747780721Z     occupants: 2
2026-05-22T14:27:30.747783791Z     budget_max: 40000
2026-05-22T14:27:30.747786741Z     caller_name: person 1
2026-05-22T14:27:30.747789741Z     listing_uuid: 85610b9d-7326-4891-b30c-29a168d61549
2026-05-22T14:27:30.747792681Z     floor_preference: 
2026-05-22T14:27:30.747795661Z     move_in_timeline: Next month
2026-05-22T14:27:30.747798722Z     qualifying_answers: {}
2026-05-22T14:27:30.747801442Z     disqualifying_reason: 
2026-05-22T14:27:30.747804472Z     qualification_status: qualified
2026-05-22T14:27:30.747807622Z   [pg resolution] path=listing_uuid property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
2026-05-22T14:27:30.747810292Z   [manager resolution] manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3
2026-05-22T14:27:30.747813302Z   [SAVED] phone=+919998064026 status=qualified property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
2026-05-22T14:27:30.747816252Z ============================================================
2026-05-22T14:27:30.747819142Z INFO:     35.163.126.218:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK
2026-05-22T14:27:34.91849187Z INFO:     49.43.27.107:0 - "GET /voice/call-status HTTP/1.1" 200 OK

### Scenario B — Multiple Listings, Caller Picks One

2026-05-22T14:31:34.043040263Z ============================================================
2026-05-22T14:31:34.043065804Z [LEASE LEAD WEBHOOK] Incoming payload
2026-05-22T14:31:34.043071684Z   message.type:     tool-calls
2026-05-22T14:31:34.043076704Z   call.id:          019e5017-0273-7000-8867-82dfc1b24464
2026-05-22T14:31:34.043081424Z   call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
2026-05-22T14:31:34.043085984Z   call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
2026-05-22T14:31:34.043090614Z   customer.number:  +919998064026
2026-05-22T14:31:34.043094974Z   [submit_lease_lead args]
2026-05-22T14:31:34.043099665Z     bedrooms: 2
2026-05-22T14:31:34.043104454Z     occupants: 1
2026-05-22T14:31:34.043112245Z     budget_max: 60000
2026-05-22T14:31:34.043116715Z     caller_name: Best Person
2026-05-22T14:31:34.043121565Z     listing_uuid: 6fdefef4-905f-456c-b7ab-e8cc43ad0c09
2026-05-22T14:31:34.043125815Z     floor_preference: High floor
2026-05-22T14:31:34.043130585Z     move_in_timeline: Flexible
2026-05-22T14:31:34.043136046Z     qualifying_answers: {"Stable source of income":"Yes","Monthly income at least 3x rent (₹1,65,000)":"Yes"}
2026-05-22T14:31:34.043140906Z     qualification_status: qualified
2026-05-22T14:31:34.043145886Z   [pg resolution] path=listing_uuid property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
2026-05-22T14:31:34.043151296Z   [manager resolution] manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3
2026-05-22T14:31:34.043155826Z   [SAVED] phone=+919998064026 status=qualified property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
2026-05-22T14:31:34.043160496Z ============================================================
2026-05-22T14:31:34.043165186Z INFO:     184.32.143.219:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK
2026-05-22T14:31:34.909064947Z INFO:     49.43.27.107:0 - "GET /voice/call-status HTTP/1.1" 200 OK
2026-05-22T14:31:45.195611855Z INFO:     49.43.27.107:0 - "GET /voice/call-status HTTP/1.1" 200 OK
2026-05-22T14:31:45.471777702Z INFO:     49.43.27.107:0 - "GET /notifications HTTP/1.1" 200 OK
2026-05-22T14:31:49.221093912Z ============================================================
2026-05-22T14:31:49.221128073Z [LEASE LEAD WEBHOOK] Incoming payload
2026-05-22T14:31:49.221134723Z   message.type:     tool-calls
2026-05-22T14:31:49.221139603Z   call.id:          019e5017-0273-7000-8867-82dfc1b24464
2026-05-22T14:31:49.221144363Z   call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
2026-05-22T14:31:49.221149163Z   call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
2026-05-22T14:31:49.221153644Z   customer.number:  +919998064026
2026-05-22T14:31:49.221158264Z   [submit_lease_lead args]
2026-05-22T14:31:49.221162844Z     bedrooms: 2
2026-05-22T14:31:49.221167714Z     occupants: 1
2026-05-22T14:31:49.221172744Z     budget_max: 60000
2026-05-22T14:31:49.221177134Z     caller_name: Test Burrison
2026-05-22T14:31:49.221181724Z     listing_uuid: 6fdefef4-905f-456c-b7ab-e8cc43ad0c09
2026-05-22T14:31:49.221186275Z     floor_preference: High floor
2026-05-22T14:31:49.221190885Z     move_in_timeline: Flexible
2026-05-22T14:31:49.221196055Z     qualifying_answers: {"Stable source of income":"Yes","Monthly income at least 3x rent (₹1,65,000)":"Yes"}
2026-05-22T14:31:49.221200795Z     qualification_status: qualified
2026-05-22T14:31:49.221206425Z   [pg resolution] path=listing_uuid property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
2026-05-22T14:31:49.221211615Z   [manager resolution] manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3
2026-05-22T14:31:49.221216325Z   [SAVED] phone=+919998064026 status=qualified property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed
2026-05-22T14:31:49.221220696Z ============================================================
2026-05-22T14:31:49.221225166Z INFO:     184.32.143.219:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK
2026-05-22T14:31:55.388687183Z INFO:     49.43.27.107:0 - "GET /voice/call-status HTTP/1.1" 200 OK
### Scenario C — Over Budget, No Match

2026-05-22T14:36:53.507616041Z ============================================================
2026-05-22T14:36:53.507641782Z [LEASE LEAD WEBHOOK] Incoming payload
2026-05-22T14:36:53.507647232Z   message.type:     tool-calls
2026-05-22T14:36:53.507651422Z   call.id:          019e501c-b8fc-7001-93ad-157586b4da88
2026-05-22T14:36:53.507655232Z   call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
2026-05-22T14:36:53.507659532Z   call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
2026-05-22T14:36:53.507674273Z   customer.number:  +919998064026
2026-05-22T14:36:53.507680103Z   [submit_lease_lead args]
2026-05-22T14:36:53.507682793Z     bedrooms: 2
2026-05-22T14:36:53.507685263Z     occupants: 1
2026-05-22T14:36:53.507688283Z     budget_max: 30000
2026-05-22T14:36:53.507690623Z     caller_name: Test Person 3
2026-05-22T14:36:53.507693063Z     listing_uuid: TM1_TEST_UNIT
2026-05-22T14:36:53.507695403Z     floor_preference: 
2026-05-22T14:36:53.507697973Z     move_in_timeline: Flexible
2026-05-22T14:36:53.507701453Z     qualifying_answers: {"stable_income":"Yes","occupants":"1","lease_term_12_months":"Yes"}
2026-05-22T14:36:53.507704113Z     disqualifying_reason: 
2026-05-22T14:36:53.507706754Z     qualification_status: qualified
2026-05-22T14:36:53.507709974Z   [pg resolution] path=shared_agent_fallback property_group_id=0205c976-dda7-4281-b87e-b27fbfbc531c
2026-05-22T14:36:53.507715814Z   [manager resolution] manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3
2026-05-22T14:36:53.507718574Z   [SAVED] phone=+919998064026 status=qualified property_group_id=0205c976-dda7-4281-b87e-b27fbfbc531c
2026-05-22T14:36:53.507721444Z ============================================================
2026-05-22T14:36:53.507724254Z INFO:     35.91.85.0:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK
2026-05-22T14:36:55.372925824Z INFO:     49.43.27.107:0 - "GET /voice/call-status HTTP/1.1" 200 OK
### Scenario D — Custom Rule Failure (Not Qualified)

2026-05-22T14:39:55.105686978Z ============================================================
2026-05-22T14:39:55.105722239Z [LEASE LEAD WEBHOOK] Incoming payload
2026-05-22T14:39:55.105729899Z   message.type:     tool-calls
2026-05-22T14:39:55.105735889Z   call.id:          019e501f-1d63-722f-b927-17f2c490a68d
2026-05-22T14:39:55.105742229Z   call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
2026-05-22T14:39:55.10574664Z   call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
2026-05-22T14:39:55.1057505Z   customer.number:  +919998064026
2026-05-22T14:39:55.105775221Z   [submit_lease_lead args]
2026-05-22T14:39:55.105782521Z     bedrooms: 2
2026-05-22T14:39:55.105790701Z     occupants: 0
2026-05-22T14:39:55.105797721Z     budget_max: 4500
2026-05-22T14:39:55.105804711Z     caller_name: The Best Person
2026-05-22T14:39:55.105810322Z     listing_uuid: 
2026-05-22T14:39:55.105814182Z     floor_preference: 
2026-05-22T14:39:55.105818152Z     move_in_timeline: Next weekend
2026-05-22T14:39:55.105822172Z     qualifying_answers: {}
2026-05-22T14:39:55.105826072Z     disqualifying_reason: 
2026-05-22T14:39:55.105829912Z     qualification_status: unmatched
2026-05-22T14:39:55.105834412Z   [pg resolution] path=shared_agent_fallback property_group_id=0205c976-dda7-4281-b87e-b27fbfbc531c
2026-05-22T14:39:55.105838642Z   [manager resolution] manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3
2026-05-22T14:39:55.105842482Z   [SAVED] phone=+919998064026 status=unmatched property_group_id=0205c976-dda7-4281-b87e-b27fbfbc531c
2026-05-22T14:39:55.105846372Z ============================================================
2026-05-22T14:39:55.105850252Z INFO:     100.23.172.106:0 - "POST /voice/lease-lead-webhook HTTP/1.1" 200 OK
### Scenario E — Income Rule Failure
1" 200 OK
2026-05-22T14:43:28.40983748Z ============================================================
2026-05-22T14:43:28.409868691Z [LEASE LEAD WEBHOOK] Incoming payload
2026-05-22T14:43:28.409874321Z   message.type:     tool-calls
2026-05-22T14:43:28.409878922Z   call.id:          019e5022-5cd2-7bb0-a1b5-70fd775d7714
2026-05-22T14:43:28.409883282Z   call.assistantId: 2dba3a50-6862-400c-861a-bfc0a45d4a95
2026-05-22T14:43:28.409904462Z   call.phoneNumberId: 969c6812-b520-468e-8f65-5fb8ca4ee240
2026-05-22T14:43:28.409907842Z   customer.number:  +919998064026
2026-05-22T14:43:28.409911002Z   [submit_lease_lead args]
2026-05-22T14:43:28.409913692Z     bedrooms: 3
2026-05-22T14:43:28.409916332Z     occupants: 0
2026-05-22T14:43:28.409919813Z     budget_max: 200000
2026-05-22T14:43:28.409922643Z     caller_name: test person 5
2026-05-22T14:43:28.409925233Z     listing_uuid: 
2026-05-22T14:43:28.409927683Z     floor_preference: 5th floor
2026-05-22T14:43:28.409930423Z     move_in_timeline: as soon as possible (flexible)
2026-05-22T14:43:28.409933003Z     qualifying_answers: {}
2026-05-22T14:43:28.409935773Z     disqualifying_reason: No 5th floor units available
2026-05-22T14:43:28.409938493Z     qualification_status: unmatched
2026-05-22T14:43:28.409941783Z   [pg resolution] path=shared_agent_fallback property_group_id=0205c976-dda7-4281-b87e-b27fbfbc531c
2026-05-22T14:43:28.409944953Z   [manager resolution] manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3
2026-05-22T14:43:28.409947793Z   [SAVED] phone=+919998064026 status=unmatched property_group_id=0205c976-dda7-4281-b87e-b27fbfbc531c
2026-05-22T14:43:28.409950393Z ============================================================

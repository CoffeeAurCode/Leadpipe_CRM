# Lease Agent Flow — Max (AI Leasing Assistant)

## Legend

| Shape | Meaning |
|---|---|
| Purple / blue box | Max speaks |
| Light green box | Caller responds |
| Orange / tan diamond | Decision / condition |
| Grey / beige box | System or CRM action |

---

## ① GREETING

```
┌──────────────────────────────────────────────┐
│  Greeting                                    │
│  "Hi! / Bonjour! I'm Max, [Owner]'s          │
│   leasing AI..."                             │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Detect caller language                      │
│  EN or FR → lock for rest of call            │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Open listening                              │
│  "Sure! What would you like to know?"        │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
```

---

## ② UNIT DISCOVERY

```
┌──────────────────────────────────────────────┐
│  Location / building                         │
│  "Which area or building are you             │
│   looking at?"                               │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
             ┌─────────────────────┐
             │  Location           │◄──────────────────────┐
             │  identified?        │                       │
             │  Match to owner's   │                       │
             │  inventory by area  │                       │
             └────┬────────────────┘                       │
                  │ Unsure                                 │
                  ▼                                        │
    ┌─────────────────────────────┐                        │
    │  Describe available areas   │                        │
    │  List owner's locations     │────────────────────────┘
    └─────────────────────────────┘
                  │ Identified
                  ▼
┌──────────────────────────────────────────────┐
│  Unit size                                   │
│  "What size are you looking for —            │
│   3.5, 4.5...?"                              │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Budget                                      │
│  "What's your budget per month?"             │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Search inventory                            │
│  Filter by location · size · budget          │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
             ┌─────────────────────┐
             │  Matching units     │
             │  found?             │
             │  Check availability │
             │  in system          │
             └────┬────────────────┘
                  │ No match
                  ▼
    ┌─────────────────────────────┐
    │  Inform caller              │
    │  No units available,        │
    │  log inquiry                │
    └─────────────────────────────┘
                  │ Match(es) found
                  ▼
┌──────────────────────────────────────────────┐
│  Present all matches                         │
│  "I have X units that fit —                  │
│   here's what's available..."                │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Caller selects a unit                       │
│  Unit confirmed → begin qualification        │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
```

---

## ③ QUALIFICATION

```
┌──────────────────────────────────────────────┐
│  Move-in date                                │
│  "When are you looking to move in?"          │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
             ┌─────────────────────┐
             │  Date aligns with   │
             │  availability?      │
             │  Compare to         │
             │  selected unit      │
             │  availability       │
             └────┬────────────────┘
                  │ Doesn't align
                  ▼
    ┌─────────────────────────────┐
    │  Note mismatch              │
    │  Log & continue             │──────────────────────────┐
    └─────────────────────────────┘                          │
                  │ Aligns                                   │
                  ▼                                          │
┌──────────────────────────────────────────────┐            │
│  Landlord awareness  ◄───────────────────────────────────-┘
│  "Does your current landlord know            │
│   you're looking?"                           │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Property questions                          │
│  "Any questions about the unit?"             │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
             ┌─────────────────────┐
             │  Caller has         │◄──────────────────────┐
             │  questions?         │                       │
             │  Pull answers from  │                       │
             │  listing data       │                       │
             └────┬────────────────┘                       │
                  │ Yes                                    │
                  ▼                                        │
    ┌─────────────────────────────┐                        │
    │  Answer dynamically         │                        │
    │  Pull from listing details  │────────────────────────┘
    └─────────────────────────────┘
                  │ No questions
                  ▼
┌──────────────────────────────────────────────┐
│  Employment status                           │
│  "Are you employed full-time,                │
│   part-time, or...?"                         │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │  Employment type?           │
         │  Full-time / part-time /    │
         │  unemployed                 │
         └──┬──────────────┬────────┬──┘
            │ Full-time    │Part-   │ Unemployed
            ▼              │time    ▼
┌────────────────┐         │  ┌────────────────┐
│ Log: full-time │         │  │ Log: unemployed│
│ Strong         │         │  │ Flag, continue │
│ qualifier      │         │  └────────┬───────┘
└───────┬────────┘         ▼           │
        │        ┌────────────────┐    │
        │        │ Log: part-time │    │
        │        │ Noted,         │    │
        │        │ continue       │    │
        │        └───────┬────────┘    │
        └────────────────┴─────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────┐
│  Number of occupants                         │
│  "How many people will be living             │
│   in the unit?"                              │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
             ┌─────────────────────┐
             │  Within unit        │
             │  capacity?          │
             │  Compare to         │
             │  selected unit max  │
             └────┬────────────────┘
                  │ Over capacity
                  ▼
    ┌─────────────────────────────┐
    │  Note & flag                │
    │  Log, continue              │──────────────────────────┐
    └─────────────────────────────┘                          │
                  │ Within capacity                          │
                  ▼                                          │
┌──────────────────────────────────────────────┐            │
│  Pets  ◄─────────────────────────────────────────────────-┘
│  "Do you have any pets?"                     │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
             ┌─────────────────────┐
             │  Pets allowed per   │
             │  policy?            │
             │  Pull from selected │
             │  unit rules         │
             └────┬────────────────┘
                  │ Not allowed
                  ▼
    ┌─────────────────────────────┐
    │  Inform caller              │
    │  Policy note, log &         │──────────────────────────┐
    │  continue                   │                          │
    └─────────────────────────────┘                          │
                  │ Allowed / no pets                        │
                  ▼                                          │
```                                                          

---

## ④ HANDOFF

```
                  ◄────────────────────────────────────────-┘
┌──────────────────────────────────────────────┐
│  Closing                                     │
│  "Thanks — I'll pass your info to            │
│   [Owner]..."                                │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Log to CRM                                  │
│  Name · phone · selected unit ·              │
│  move-in date · Employment ·                 │
│  occupants · pets                            │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Lead created in CRM                         │
│  Owner reviews & follows up                  │
└──────────────────────────────────────────────┘
```

---

## Data collected per call

| Field | Collected at step |
|---|---|
| Language (EN / FR) | ① Greeting — detect |
| Location / building | ② Unit Discovery |
| Unit size | ② Unit Discovery |
| Budget | ② Unit Discovery |
| Selected unit | ② Unit Discovery — caller selects |
| Move-in date | ③ Qualification |
| Current landlord awareness | ③ Qualification |
| Employment type | ③ Qualification |
| Number of occupants | ③ Qualification |
| Pets | ③ Qualification |

---

## Branch outcomes

| Condition | Outcome |
|---|---|
| Location unsure | List available areas, re-ask |
| No inventory match | Inform caller, log inquiry, end |
| Move-in date mismatch | Note mismatch, log, continue |
| Caller has property questions | Answer from listing data, loop back |
| Full-time employment | Log as strong qualifier |
| Part-time employment | Log, continue |
| Unemployed | Flag, continue |
| Over occupancy capacity | Note & flag, continue |
| Pets not allowed | Inform caller, log, continue |

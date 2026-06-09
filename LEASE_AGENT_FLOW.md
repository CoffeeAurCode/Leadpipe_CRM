# Lease Agent (Max) — Conversation Flow

**Legend**
| Symbol | Meaning |
|--------|---------|
| 🟣 | Max speaks |
| 🟢 | Caller input / decision |
| ⬜ | System action |
| 🟠 | Branch decision |

---

## Quebec Apartment Size Reference

Quebec uses a unique sizing system rooted in the architecture of its classic duplexes and triplexes. The convention stuck and is now universal across the province.

**Formula:** count all full rooms (bedroom, living room, kitchen), then add ½ for the one bathroom.

> e.g. 1 bedroom + 1 living room + 1 kitchen + 1 bathroom = **3½**

| Quebec | Rest of Canada / World |
|--------|----------------------|
| 1½ | Studio |
| 2½ | Bachelor |
| 3½ | 1-bedroom |
| 4½ | 2-bedroom |
| 5½ | 3-bedroom |

Max uses this lingo natively when asking Q3 and when pitching units.

---

## 1. Entry Point

🟣 **Greeting**
> "Hi, this is Max — AI leasing assistant. Which unit are you inquiring about?"

---

## 2. Branch — Does the caller have a specific unit in mind?

🟠 **Caller has a specific unit?** *(Named unit / address vs. general inquiry)*

| Answer | Path |
|--------|------|
| General inquiry | → [Discovery Flow](#3a-discovery-flow) |
| Yes, specific unit | → [Specific Unit Flow](#3b-specific-unit-flow) |

---

## 3a. Discovery Flow

### Step 1 — Acknowledge
🟣 "Of course! Let me help you find something."

### Step 2 — Collect Preferences (Q1–Q5)

| # | Question | Max says |
|---|----------|----------|
| Q1 | City | "Which city are you looking in?" |
| Q2 | Area | "Any specific neighbourhood or area?" |
| Q3 | Unit size | "What size — 3½, 4½, or number of bedrooms?" |
| Q4 | Budget | "What monthly rent are you comfortable with?" |
| Q5 | Move-in date | "When are you looking to move in?" |

### Step 3 — Inventory Lookup
⬜ **CRM query** — city → area → size → budget → move-in date

### Step 4 — Match found?

🟠 **Unshown unit fits all filters?**

| Result | Path |
|--------|------|
| No | → [No Match](#no-match) |
| Yes | → [Pitch Unit](#pitch-unit) |

---

### No Match

🟣 "Nothing available right now — I'll pass your info to the team."

⬜ **Collect contact** — Log to CRM, flag for follow-up

> *(End of call)*

---

### Pitch Unit

🟣 "I have a 3½ on Rue X at $1,100/mo — does that interest you?"

🟠 **Caller interested?**

| Answer | Action |
|--------|--------|
| No | Try next unit → loop back to **Pitch Unit** |
| Yes | → **Begin Qualification** |

🟣 **Begin Qualification**
> "Perfect — I'll ask a few quick questions to get you set up."

→ Proceed to [Qualification Flow](#5-qualification-flow)

---

## 3b. Specific Unit Flow

🟣 **Confirm unit**
> "Great — I'll ask a few quick questions."

→ Proceed directly to [Qualification Flow](#5-qualification-flow)

---

## 5. Qualification Flow

⬜ Collect the following details:

- Employment
- Number of occupants
- Pets
- Smoking
- Contact information

---

## 6. CRM Handoff

⬜ **CRM handoff + notify landlord**

> *(End of call)*

---

## Summary Flowchart (text)

```
Greeting
  └─ Specific unit? ──Yes──► Confirm unit ──► Qualification flow ──► CRM handoff
         │
       General
         │
       Acknowledge
         │
       Q1 City → Q2 Area → Q3 Size → Q4 Budget → Q5 Move-in
         │
       Inventory lookup (CRM)
         │
       Match found? ──No──► No match ──► Collect contact
         │
        Yes
         │
       Pitch unit ◄──────────────────────────────────┐
         │                                            │
       Interested? ──No── try next unit ──────────────┘
         │
        Yes
         │
       Begin qualification
         │
       Qualification flow (employment, occupants, pets, smoking, contact)
         │
       CRM handoff + notify landlord
```

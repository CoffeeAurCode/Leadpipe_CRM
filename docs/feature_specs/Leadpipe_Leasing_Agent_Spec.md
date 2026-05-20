**LEADPIPE**

**AI Leasing Agent — Feature Specification**

|  |  |
| --- | --- |
| **Prepared for** | Development Team |
| **Prepared by** | Shaun (Product) |
| **Feature** | AI Voice Leasing Agent + Conditional Logic |
| **Version** | v1.0 — Initial Spec |
| **Date** | May 17, 2026 |

# **1. Overview & Concept**

This document outlines the full conditional flow, logic, and feature requirements for the Leadpipe AI Leasing Agent. The agent acts as an automated front desk for landlords and property managers, handling inbound calls from prospective tenants, identifying the property of interest, qualifying the lead against property-specific criteria, and inserting qualified leads into the CRM under the correct property.

Think of it as a 24/7 AI leasing front desk that never misses a call, always qualifies, and automatically logs leads into the right place.

# **2. How It Works — End-to-End Flow**

## **2.1 The Landlord Setup (Back-End Configuration)**

Before the agent can work, the property owner (the Leadpipe user) must configure their account with the following:

**Property Listings**

* Each unit/property is added to the system with:
* Full street address (civic number, street name, city, unit number if applicable)
* Property type (apartment, condo, house, duplex, etc.)
* Number of bedrooms / bathrooms
* Monthly rent and lease term
* Availability date
* Custom property rules (see section 2.3)

**Custom Property Rules (Per Unit)**

Each property listing should allow the owner to toggle or define qualifying criteria. Suggested defaults include:

* Smoking allowed: Yes / No
* Pets allowed: Yes / No / Dogs only / Cats only / Small pets only
* Minimum income requirement (e.g. 3x monthly rent)
* Credit check required: Yes / No
* Maximum number of occupants
* First & last month required: Yes / No
* Short-term lease considered: Yes / No
* Custom question field (free text — e.g. "Are you a student?")

**Note:** *These rules drive the qualifying questions the agent asks on the call. The agent should only ask questions relevant to the rules enabled for that specific property.*

## **2.2 Inbound Call Flow — Step by Step**

When a lead calls the Leadpipe-assigned phone number:

**Step 1 — Greeting & Property Identification**

The agent greets the caller and asks which property they are calling about.

* Agent asks for the street address and unit number of the property they saw advertised.
* The agent searches the system for a matching listing.
* If found: agent confirms the property and proceeds to qualification.
* If not found: agent apologizes and asks the caller to double-check the address, or offers to look for similar available properties (see Section 2.4).

**Step 2 — Property Confirmation**

Once the property is identified, the agent briefly confirms key details back to the lead:

* Address and unit
* Number of bedrooms / bathrooms
* Monthly rent
* Availability date

Agent then asks: "Does that sound like the right property?"

**Step 3 — Qualifying Questions**

The agent runs through the qualifying questions tied to that specific property. Standard qualifying questions (research-backed) include:

* Move-in date: "When are you looking to move in?"
* Group size: "How many people will be living in the unit?"
* Employment: "Are you currently employed or have a stable source of income?"
* Income: "Would you be able to provide proof of income (pay stubs, employment letter, etc.)?"
* Rental history: "Have you rented before? Do you have references from a previous landlord?"
* Credit: "Are you comfortable with a credit check being run as part of the application?"
* Pets (if rule enabled): "Do you have any pets?"
* Smoking (if rule enabled): "Are you a smoker?"
* Lease term: "Are you looking for a long-term lease (12 months+)?"
* ID: "Do you have valid government-issued ID?"

**Note:** *The agent should only ask questions that are relevant to the property rules enabled by the landlord. If pets are allowed with no restrictions, skip the pet question entirely.*

**Step 4 — Lead Qualification Result**

Based on the caller’s answers, the system determines one of two outcomes:

* QUALIFIED: Lead meets all criteria. Agent thanks them, confirms next steps (application, viewing, callback from owner), and inserts them into the CRM.
* NOT QUALIFIED: Lead fails one or more hard criteria. Agent politely informs them they may not be the right fit for that specific property, but can check if anything else is available (see Section 2.4).

**Note:** *Disqualification should be handled gracefully. The agent should never be blunt or rude. It should acknowledge the situation and offer alternatives where possible.*

**Step 5 — CRM Insertion**

Qualified leads are automatically inserted into the system under the correct property listing, categorized as "New Inquiries". The CRM record should capture:

* Full name
* Phone number
* Email (if provided)
* Property inquired about
* Move-in date requested
* Number of occupants
* Qualifying answers (summary)
* Qualification status (Qualified / Not Qualified)
* Timestamp of call
* Call duration

## **2.3 Property Not Found — Fallback Logic**

If the caller’s stated address does not match any active listing in the system, the agent should:

* Ask the caller to repeat or spell out the address.
* If still no match: inform the caller the system doesn’t have an active listing at that address.
* Offer to check if there are other available properties that may suit their needs (bedroom count, city, budget).
* If a match is found elsewhere: proceed with qualifying the lead for the alternative property.
* If no alternatives: take their contact info and preferred criteria, and log as an unmatched inquiry for the landlord to follow up on.

## **2.4 Alternative Property Search (Cross-Listing Flow)**

At any point during the call — before, during, or after qualification — the lead may express interest in a different type of unit (e.g., they want more space, an extra bathroom, a lower price point). When this happens:

* Agent acknowledges the change in criteria.
* Agent searches available listings in the system for a match based on:
* Bedroom count
* Bathroom count
* City / area
* Budget (if stated)
* Move-in date
* If a match is found: agent presents it to the caller and resumes qualification for the new property.
* If no match is found: agent takes their info and preferred criteria and logs an unmatched inquiry.

This makes the agent function like a real leasing front desk — not just a script runner, but an active assistant that can pivot and match leads to inventory.

# **3. Leasing Agent Dashboard Tab**

A dedicated "Leasing Agent" tab should be added to the Leadpipe dashboard to give landlords full visibility into agent activity and performance.

## **3.1 Metrics to Display**

* Total calls received
* Total leads qualified
* Total leads disqualified
* Qualification rate (%)
* Average call duration
* Estimated time saved (based on avg call duration vs manual processing)
* Calls by property (breakdown per listing)
* Unmatched inquiries (calls where no property was found)
* Missed calls / voicemails (if applicable)

## **3.2 Lead Log**

A scrollable log showing each call/inquiry with:

* Caller name & number
* Property inquired about
* Qualification result (badge: Qualified / Not Qualified / Unmatched)
* Date & time
* Call duration
* Quick view button to see full qualifying answers

## **3.3 Filters & Export**

* Filter by: property, date range, qualification status
* Export to CSV or PDF

# **4. Key Business Logic Rules**

* The agent must only qualify leads against the rules set for the specific property being inquired about.
* If a property has no custom rules set, the agent uses a default qualifying flow (standard questions only).
* The same phone number can serve multiple properties — the system identifies which property based on what the caller states, not a dedicated per-property number (though per-property numbers should also be supported if needed).
* A lead can only be qualified for one property per call session, unless they express interest in switching (cross-listing flow).
* Leads that fail qualification should still be logged — just marked as "Not Qualified" with the disqualifying reason noted.
* All calls should be recorded and linked to the lead record (if recording is enabled by the user).

# **5. Out of Scope (For Now)**

The following are intentionally excluded from this initial build and can be revisited in a later sprint:

* Automated scheduling of property viewings
* Email follow-ups post-call
* Multi-language support
* Integration with external listing platforms (Kijiji, Marketplace, etc.)
* Tenant scoring / AI-generated risk assessment

# **6. Questions / Open Items for Dev**

* How are alternate property matches ranked? Closest match by bedroom count first? Or by availability date?
* What is the fallback if the AI cannot parse an address correctly? Human handoff? Error message?
* Should disqualified leads be visible to the landlord before they are archived, or auto-archived?
* Is "estimated time saved" calculated based on a fixed benchmark per call, or configurable by the admin?
* Should there be a max number of properties per account for this feature in the MVP?


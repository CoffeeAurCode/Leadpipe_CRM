# Chatbot Capabilities

All capabilities require explicit user confirmation before any write/delete operation.

---

## Properties
| Action | Example Prompt |
|---|---|
| List all properties | "Show all properties" |
| Add a property | "Add a property called Sunrise Heights at 12 Main Street" |
| Delete a property | "Delete the property Sunrise Heights" |

## Buildings
| Action | Example Prompt |
|---|---|
| List all buildings | "List all buildings" |
| Add a building | "Add a building called Block A to Sunrise Heights" |
| Delete a building | "Delete building Block A" |

## Units / Flats
| Action | Example Prompt |
|---|---|
| Add a unit | "Add unit 4B to Block A" |
| Delete a unit | "Delete unit 101" |
| View unit details | "Show details for flat 101" |

## Tenants
| Action | Example Prompt |
|---|---|
| Look up by name | "Find tenant John Smith" |
| Look up by phone | "Who is the tenant with phone 9876543210?" |
| Look up by flat | "Who lives in flat 101?" |

## Appointments
| Action | Example Prompt |
|---|---|
| View by date | "What appointments are there for tomorrow?" |
| View by ID | "Show appointment details for ID 12" |
| View by flat | "Show all appointments for flat 202" |
| Reschedule | "Reschedule appointment 5 to March 25 at 3pm" |
| Cancel | "Cancel appointment 5" |
| Mark as attended | "Mark appointment 5 as attended" |
| Reactivate cancelled | "Change appointment 5 status back to scheduled" |

## Complaints
| Action | Example Prompt |
|---|---|
| View all complaints | "Show all complaints" |
| Filter by flat | "Show complaints for flat 101" |
| Filter by status | "Show all pending complaints" |
| Filter by flat + status | "Show resolved complaints for flat 202" |

---

## Rules
- The bot always asks for confirmation before any add, update, reschedule, cancel, or delete.
- Reschedule and cancel use only the appointment ID the user explicitly provides — it will not substitute a different ID.
- If a requested action has no corresponding tool, the bot will say so clearly rather than pretending it succeeded.

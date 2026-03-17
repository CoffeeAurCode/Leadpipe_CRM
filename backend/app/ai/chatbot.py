"""
AI Chatbot module using Groq for property management assistance.
Supports tool calling for tenant, unit, building, and appointment operations.
"""
import json
from datetime import datetime
from openai import OpenAI, BadRequestError
from supabase import Client
from app.config import settings

MAX_TOOL_CALL_TURNS = 5

# Base prompt — today's date is injected at request time in run_chat()
_SYSTEM_PROMPT_BASE = """You are a property management assistant for a tenant management dashboard.
You help managers manage the full property hierarchy: properties → buildings → units.
You can add/delete properties, add/delete buildings (and link them to properties), add/delete units, retrieve tenant information, and check or reschedule appointments.
Be concise and professional.

Rules you must always follow:
- Before performing any write or delete operation (add, update, reschedule, delete), always ask the user for explicit confirmation first.
- When rescheduling, use ONLY the appointment ID that the user explicitly stated. If that appointment is not found, tell the user it does not exist — do NOT substitute a different appointment ID.
- When adding a unit, look up the building by the name the user provides. Do not ask for a building ID.
- CRITICAL: Never claim an action was completed unless you received a success result from the tool. If a tool returns an error or is unavailable, tell the user exactly what happened.
- CRITICAL: You can ONLY perform actions that have a corresponding tool. If the user asks for something you have no tool for, say so clearly — do NOT pretend the action succeeded.
- Today's date is {today}. Use this when the user says "today", "tomorrow", "yesterday", etc."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_new_unit",
            "description": "Add a new unit/flat to a building. Looks up the building by name automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flat_number": {
                        "type": "string",
                        "description": "The unit/flat identifier (e.g. '4B', 'A101')"
                    },
                    "address": {
                        "type": "string",
                        "description": "The full address of the unit (optional)"
                    },
                    "building_name": {
                        "type": "string",
                        "description": "The name of the building this unit belongs to (will be looked up by name)"
                    }
                },
                "required": ["flat_number", "building_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_new_building",
            "description": "Add a new building to the system, optionally linking it to a property by name. Checks if it already exists before creating.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the building"
                    },
                    "address": {
                        "type": "string",
                        "description": "The full address of the building (optional)"
                    },
                    "property_name": {
                        "type": "string",
                        "description": "The name of the property/property group this building belongs to (optional, looked up by name)"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_properties",
            "description": "List all properties (property groups) in the system, optionally filtered by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name_filter": {
                        "type": "string",
                        "description": "Optional partial name to filter properties by"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_new_property",
            "description": "Add a new property (property group) to the system. A property is the top-level entity that contains buildings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the property"
                    },
                    "address": {
                        "type": "string",
                        "description": "The address of the property (optional)"
                    },
                    "description": {
                        "type": "string",
                        "description": "A short description of the property (optional)"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_property",
            "description": "Delete a property by its ID. The property must have no buildings linked to it. Use list_properties first to find the ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {
                        "type": "string",
                        "description": "The exact ID of the property to delete"
                    }
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_unit",
            "description": "Delete a unit/flat by its flat number. The unit must not be occupied by a tenant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flat_number": {
                        "type": "string",
                        "description": "The flat/unit number to delete (e.g. 'T33', 'A101')"
                    }
                },
                "required": ["flat_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_tenant_details",
            "description": "Retrieve details about a tenant by their name or phone number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tenant_name": {
                        "type": "string",
                        "description": "The tenant's full name (partial match supported)"
                    },
                    "phone_number": {
                        "type": "string",
                        "description": "The tenant's phone number"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_appointments_by_date",
            "description": "Check all appointments scheduled for a specific date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date to check appointments for (format: YYYY-MM-DD)"
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_buildings",
            "description": "List all buildings in the system, optionally filtered by name. Use this to find duplicates or check what buildings exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name_filter": {
                        "type": "string",
                        "description": "Optional partial name to filter buildings by (e.g. 'Test' to find all buildings with 'Test' in the name)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_building",
            "description": "Delete a building by its ID. The building must have no units/flats associated with it. Use list_buildings first to find the ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "building_id": {
                        "type": "string",
                        "description": "The exact ID of the building to delete"
                    }
                },
                "required": ["building_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_appointment",
            "description": "Reschedule an existing appointment to a new date and time. Only use the appointment ID explicitly provided by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "integer",
                        "description": "The exact ID of the appointment to reschedule, as stated by the user"
                    },
                    "new_date": {
                        "type": "string",
                        "description": "The new date and time (format: YYYY-MM-DD HH:MM:SS)"
                    }
                },
                "required": ["appointment_id", "new_date"]
            }
        }
    }
]


def execute_tool(tool_name: str, args: dict, db: Client) -> str:
    try:
        if tool_name == "add_new_unit":
            flat_number = args.get("flat_number")
            address = args.get("address")
            building_name = args.get("building_name")

            if not flat_number:
                return "Missing required field: flat_number."
            if not building_name:
                return "Missing required field: building_name."

            # Look up building by name
            building_res = db.table("buildings").select("id, name, address").ilike("name", f"%{building_name}%").execute()
            if not building_res.data:
                return f"No building found with name '{building_name}'. Please check the building name or add the building first."
            if len(building_res.data) > 1:
                options = ", ".join(f"'{b.get('name')}' (ID: {b.get('id')})" for b in building_res.data)
                return f"Multiple buildings match '{building_name}': {options}. Please be more specific."
            building_id = building_res.data[0].get("id")

            # Check for duplicate flat number
            existing = db.table("flats").select("id").ilike("flat_number", flat_number).execute()
            if existing.data:
                return f"A unit with flat number '{flat_number}' already exists."

            payload = {"flat_number": flat_number, "building_id": building_id}
            if address:
                payload["address"] = address

            result = db.table("flats").insert(payload).execute()

            if result.data:
                location = f" at '{address}'" if address else ""
                return f"Unit '{flat_number}'{location} successfully added to building '{building_res.data[0].get('name')}'."
            return "Failed to add unit. Please try again."

        elif tool_name == "add_new_building":
            name = args.get("name")
            address = args.get("address")
            property_name = args.get("property_name")

            if not name:
                return "Missing required field: name."

            # Check for duplicate building name
            existing = db.table("buildings").select("id, name, address").ilike("name", name).execute()
            if existing.data:
                b = existing.data[0]
                return (
                    f"A building named '{b.get('name')}' already exists at '{b.get('address')}' "
                    f"(ID: {b.get('id')}). Use this building to add units."
                )

            payload = {"name": name}
            if address:
                payload["address"] = address

            # Optionally link to a property by name
            if property_name:
                prop_res = db.table("properties_list").select("id, name").ilike("name", f"%{property_name}%").execute()
                if not prop_res.data:
                    return f"No property found with name '{property_name}'. Add the property first or check the name."
                if len(prop_res.data) > 1:
                    opts = ", ".join(f"'{p.get('name')}' (ID: {p.get('id')})" for p in prop_res.data)
                    return f"Multiple properties match '{property_name}': {opts}. Please be more specific."
                payload["property_id"] = prop_res.data[0].get("id")

            result = db.table("buildings").insert(payload).execute()

            if result.data:
                building = result.data[0]
                location = f" at '{address}'" if address else ""
                msg = f"Building '{name}'{location} successfully created with ID {building.get('id')}."
                if property_name:
                    msg += f" Linked to property '{prop_res.data[0].get('name')}'."
                return msg
            return "Failed to add building. Please try again."

        elif tool_name == "get_tenant_details":
            tenant_name = args.get("tenant_name")
            phone_number = args.get("phone_number")

            if not tenant_name and not phone_number:
                return "Please provide either a tenant name or phone number to search."

            query = db.table("tenants").select(
                "name, phone, lease_start_date, lease_end_date, rent_status, payment_schedule, manager_notes"
            )

            if phone_number:
                query = query.eq("phone", phone_number)
            elif tenant_name:
                query = query.ilike("name", f"%{tenant_name}%")

            result = query.execute()

            if not result.data:
                return "No tenant found matching that query."

            tenants = result.data
            if len(tenants) == 1:
                t = tenants[0]
                return (
                    f"Tenant: {t.get('name')}\n"
                    f"Phone: {t.get('phone')}\n"
                    f"Rent Status: {t.get('rent_status')}\n"
                    f"Lease: {t.get('lease_start_date')} to {t.get('lease_end_date')}\n"
                    f"Payment Schedule: {t.get('payment_schedule')}\n"
                    f"Notes: {t.get('manager_notes') or 'None'}"
                )
            names = [t.get("name") for t in tenants]
            return (
                f"Found {len(tenants)} tenants matching '{tenant_name}': {', '.join(names)}. "
                f"Please be more specific or use a phone number."
            )

        elif tool_name == "check_appointments_by_date":
            date = args.get("date")
            if not date:
                return "Missing required field: date."

            from dateutil import parser as dateparser
            try:
                parsed = dateparser.parse(date)
                formatted_date = parsed.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                return "Invalid date format. Please use YYYY-MM-DD (e.g. 2025-06-15)."

            start = f"{formatted_date} 00:00:00"
            end = f"{formatted_date} 23:59:59"

            result = (
                db.table("appointments")
                .select("id, flat_number, appointment_date, status")
                .gte("appointment_date", start)
                .lte("appointment_date", end)
                .order("appointment_date")
                .execute()
            )

            if not result.data:
                return f"No appointments found for {formatted_date}."

            lines = [f"Appointments for {formatted_date}:"]
            for apt in result.data:
                lines.append(
                    f"- ID {apt['id']} | Flat {apt.get('flat_number', 'N/A')} | "
                    f"{apt.get('appointment_date', 'N/A')} | Status: {apt.get('status', 'N/A')}"
                )
            return "\n".join(lines)

        elif tool_name == "reschedule_appointment":
            appointment_id = args.get("appointment_id")
            new_date = args.get("new_date")

            if not appointment_id:
                return "Missing required field: appointment_id."
            if not new_date:
                return "Missing required field: new_date."

            from dateutil import parser as dateparser
            try:
                parsed = dateparser.parse(new_date)
                # Store with T separator so parseISO in the frontend calendar works correctly
                normalized_date = parsed.strftime("%Y-%m-%dT%H:%M:%S")
            except (ValueError, TypeError):
                return "Invalid date format. Please use YYYY-MM-DD HH:MM:SS (e.g. 2025-06-15 10:00:00)."

            fetch = db.table("appointments").select("id, status").eq("id", appointment_id).execute()
            if not fetch.data:
                return f"No appointment found with ID {appointment_id}. Please verify the appointment ID and try again."

            apt = fetch.data[0]
            if apt.get("status") == "completed":
                return "Cannot reschedule a completed appointment."
            if apt.get("status") == "cancelled":
                return "Cannot reschedule a cancelled appointment."

            update = (
                db.table("appointments")
                .update({"appointment_date": normalized_date})
                .eq("id", appointment_id)
                .execute()
            )

            if update.data:
                return f"Appointment {appointment_id} successfully rescheduled to {normalized_date}."
            return "Failed to reschedule appointment. Please try again."

        elif tool_name == "list_buildings":
            name_filter = args.get("name_filter", "")
            query = db.table("buildings").select("id, name, address")
            if name_filter:
                query = query.ilike("name", f"%{name_filter}%")
            result = query.order("name").execute()

            if not result.data:
                msg = f"No buildings found matching '{name_filter}'." if name_filter else "No buildings found."
                return msg

            lines = [f"Found {len(result.data)} building(s):"]
            for b in result.data:
                lines.append(f"- ID: {b.get('id')} | Name: {b.get('name')} | Address: {b.get('address')}")
            return "\n".join(lines)

        elif tool_name == "delete_building":
            building_id = args.get("building_id")
            if not building_id:
                return "Missing required field: building_id."

            # Verify the building exists
            fetch = db.table("buildings").select("id, name").eq("id", building_id).execute()
            if not fetch.data:
                return f"No building found with ID '{building_id}'."

            building_name = fetch.data[0].get("name")

            # Safety check: refuse if the building has any units
            flats_check = db.table("flats").select("id").eq("building_id", building_id).execute()
            if flats_check.data:
                return (
                    f"Cannot delete building '{building_name}' (ID: {building_id}) — "
                    f"it has {len(flats_check.data)} unit(s) linked to it. "
                    f"Remove all units from this building first."
                )

            db.table("buildings").delete().eq("id", building_id).execute()
            return f"Building '{building_name}' (ID: {building_id}) has been deleted."

        elif tool_name == "list_properties":
            name_filter = args.get("name_filter", "")
            query = db.table("properties_list").select("id, name, address, description")
            if name_filter:
                query = query.ilike("name", f"%{name_filter}%")
            result = query.order("name").execute()

            if not result.data:
                msg = f"No properties found matching '{name_filter}'." if name_filter else "No properties found."
                return msg

            lines = [f"Found {len(result.data)} property/properties:"]
            for p in result.data:
                lines.append(
                    f"- ID: {p.get('id')} | Name: {p.get('name')} | Address: {p.get('address') or 'N/A'}"
                )
            return "\n".join(lines)

        elif tool_name == "add_new_property":
            name = args.get("name")
            address = args.get("address")
            description = args.get("description")

            if not name:
                return "Missing required field: name."

            # Check for duplicate property name
            existing = db.table("properties_list").select("id, name").ilike("name", name).execute()
            if existing.data:
                p = existing.data[0]
                return f"A property named '{p.get('name')}' already exists (ID: {p.get('id')})."

            payload = {"name": name}
            if address:
                payload["address"] = address
            if description:
                payload["description"] = description

            result = db.table("properties_list").insert(payload).execute()
            if result.data:
                prop = result.data[0]
                return f"Property '{name}' successfully created with ID {prop.get('id')}."
            return "Failed to add property. Please try again."

        elif tool_name == "delete_property":
            property_id = args.get("property_id")
            if not property_id:
                return "Missing required field: property_id."

            fetch = db.table("properties_list").select("id, name").eq("id", property_id).execute()
            if not fetch.data:
                return f"No property found with ID '{property_id}'."

            property_name = fetch.data[0].get("name")

            # Safety check: refuse if any buildings are linked
            buildings_check = db.table("buildings").select("id").eq("property_id", property_id).execute()
            if buildings_check.data:
                return (
                    f"Cannot delete property '{property_name}' (ID: {property_id}) — "
                    f"it has {len(buildings_check.data)} building(s) linked to it. "
                    f"Remove all buildings from this property first."
                )

            db.table("properties_list").delete().eq("id", property_id).execute()
            return f"Property '{property_name}' (ID: {property_id}) has been deleted."

        elif tool_name == "delete_unit":
            flat_number = args.get("flat_number")
            if not flat_number:
                return "Missing required field: flat_number."

            fetch = db.table("flats").select("id, flat_number, occupied, tenant_uuid").ilike("flat_number", flat_number).execute()
            if not fetch.data:
                return f"No unit found with flat number '{flat_number}'."
            if len(fetch.data) > 1:
                opts = ", ".join(f"'{f.get('flat_number')}'" for f in fetch.data)
                return f"Multiple units match '{flat_number}': {opts}. Please be more specific."

            unit = fetch.data[0]
            if unit.get("occupied") or unit.get("tenant_uuid"):
                return (
                    f"Cannot delete unit '{unit.get('flat_number')}' — it is currently occupied by a tenant. "
                    f"Remove the tenant first."
                )

            db.table("flats").delete().eq("id", unit.get("id")).execute()
            return f"Unit '{unit.get('flat_number')}' has been deleted."

        else:
            return f"Unknown tool: {tool_name}."

    except Exception as e:
        return f"Tool execution error: {str(e)}"


def run_chat(messages: list, db: Client) -> str:
    client = OpenAI(api_key=settings.OPEN_AI_API)

    today = datetime.now().strftime("%A, %B %d, %Y")
    system_content = _SYSTEM_PROMPT_BASE.format(today=today)
    system_message = {"role": "system", "content": system_content}

    truncated = messages[-10:] if len(messages) > 10 else messages
    full_messages = [system_message] + truncated

    for _ in range(MAX_TOOL_CALL_TURNS):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=full_messages,
                tools=TOOLS,
                tool_choice="auto",
            )
        except BadRequestError:
            # Fallback to plain completion if tool calling fails
            fallback = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=full_messages,
            )
            return fallback.choices[0].message.content or "I'm sorry, I couldn't process that request."

        msg = response.choices[0].message

        # Append assistant message (with tool_calls if present)
        assistant_entry = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        full_messages.append(assistant_entry)

        # No tool calls → final answer
        if not msg.tool_calls:
            return msg.content or "I'm sorry, I couldn't generate a response."

        # Execute each tool call and append results
        for tool_call in msg.tool_calls:
            try:
                tool_args = json.loads(tool_call.function.arguments)
            except (json.JSONDecodeError, TypeError):
                tool_args = {}

            result = execute_tool(tool_call.function.name, tool_args, db)

            full_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    return "I've reached the maximum number of steps. Please try rephrasing your request."

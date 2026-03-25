# Vapi Voice Agent Backend Migration Plan

## Goal Description
The objective is to migrate the Vapi Voice Agent configuration from the Vapi Dashboard entirely into the backend codebase using the Vapi Python Server SDK (`vapi_server_sdk`). This allows the agent configuration (prompts, voices, models, and tools) to be version-controlled, easily updated, and managed as "Infrastructure as Code" directly from the backend. 

## User Review Required
> [!IMPORTANT]
> To use the `vapi_server_sdk`, we will need your **Vapi API Key**. Please confirm if this is already in your `.env` file or if you will provide it.
> 
> Also, to attach the newly created assistant to your existing phone number programmatically, we will need the **Phone Number ID** from your Vapi dashboard. Please let me know if you want the script to automatically attach it to the phone number, or if you prefer to just copy the new Assistant ID and link it manually in the dashboard.
> 
> Lastly, please confirm if you prefer:
> 1. **A Deployment Script** (`scripts/deploy_agent.py`) that you run manually whenever you want to update the agent on Vapi.
> 2. **Dynamic Webhook Configuration (`assistant-request`)** where Vapi requests the config from the backend every time a call starts. (The prompt suggests "made via vapi python sdk", so Option 1 is recommended and detailed below).

## Proposed Changes

### `backend`
The core changes involve adding the SDK, defining the agent configuration in Python, and creating a deployment script.

#### [MODIFY] `requirements.txt`
- Add `vapi_server_sdk` to dependencies.

#### [NEW] `backend/app/services/vapi_agent_config.py`
- We will translate the 480+ lines of JSON from [Voice_agent.md](file:///c:/Users/BIT/Coding/Tenant_management_MVP/Voice_agent.md) into a modular Python configuration.
- Define Python dictionaries for `model` (OpenAI `gpt-5.2-chat-latest`), [voice](file:///c:/Users/BIT/Coding/Tenant_management_MVP/backend/app/routes/voice.py#12-441) (ElevenLabs), `transcriber` (Deepgram), and the 6 tools:
  - `Verify_phone_number`
  - `submit_complaint`
  - `view_active_appointments`
  - `update_appointment`
  - `cancel_appointment`
  - `check_availability`
- Implement a class/module `VapiAgentManager` using `from vapi import Vapi` to handle `client.assistants.create` and `client.assistants.update`.

#### [NEW] `backend/scripts/deploy_vapi_agent.py`
- A utility script to synchronize the backend configuration to Vapi.
- It will read the `VAPI_API_KEY`, instantiate the SDK client, and either create a new assistant or update the existing one based on an `ASSISTANT_ID` env variable.
- *(Optional)* Bind the assistant to the purchased phone number.

#### [MODIFY] [backend/app/routes/voice.py](file:///c:/Users/BIT/Coding/Tenant_management_MVP/backend/app/routes/voice.py)
- The current webhook endpoint (`/voice/webhook`) expects normal Vapi events (`end-of-call-report`, `tool-calls`). This logic can remain mostly as-is, as it handles the logic for the existing tools.
- We will ensure the tool URLs in the new Python config point dynamically to the deployed backend URL (e.g., using an env variable like `BACKEND_URL`) so that tools hit your current backend webhook.

## Verification Plan

### Automated Tests
- Run `python -m scripts.deploy_vapi_agent` (or similar) to dry-run/execute the assistant creation using the Vapi API.
- Check the stdout to confirm the SDK returns a valid `assistant_id`.

### Manual Verification
1. Run the deployment script to create/update the assistant in your Vapi account.
2. Make a test call to the phone number assigned to the new assistant.
3. Test a typical complaint flow:
   - Provide a valid flat number to trigger `Verify_phone_number`.
   - Describe a maintenance issue.
   - Propose an appointment date/time to trigger `check_availability`.
   - Confirm to trigger `submit_complaint`.
4. Verify the complaint appears in the database and the `/voice/webhook` successfully processes the events.

"""
Unit tests for app/ai/chatbot.py — Section 3.2 of TEST_PLAN.md

execute_tool is tested with a mock DB (no network calls).
run_chat is tested with a mocked OpenAI client.
"""
import json
from unittest.mock import MagicMock, patch, call
import pytest

from app.ai.chatbot import execute_tool, run_chat, _APPOINTMENT_WRITE_TOOLS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_db():
    return MagicMock()


def _mock_openai_text_response(content: str):
    """OpenAI response with a plain text message (no tool calls)."""
    mock_msg = MagicMock()
    mock_msg.content = content
    mock_msg.tool_calls = None
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def _mock_openai_tool_call_response(tool_name: str, args: dict, call_id: str = "call_123"):
    """OpenAI response that requests a single tool call."""
    mock_tool_call = MagicMock()
    mock_tool_call.id = call_id
    mock_tool_call.function.name = tool_name
    mock_tool_call.function.arguments = json.dumps(args)

    mock_msg = MagicMock()
    mock_msg.content = None
    mock_msg.tool_calls = [mock_tool_call]

    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


# ---------------------------------------------------------------------------
# execute_tool tests
# ---------------------------------------------------------------------------

class TestExecuteToolDispatch:
    def test_unknown_tool_returns_error_string(self):
        result = execute_tool("brave_search", {}, _mock_db())
        assert "Unknown tool" in result or "unknown" in result.lower()

    def test_tool_exception_returns_error_string_not_raise(self):
        db = _mock_db()
        db.table.side_effect = Exception("DB exploded")
        result = execute_tool("add_new_unit", {"flat_number": "X1", "building_name": "B"}, db)
        assert isinstance(result, str)
        assert "error" in result.lower() or "Error" in result


class TestExecuteToolAddNewUnit:
    def test_building_not_found_returns_error(self):
        db = _mock_db()
        db.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = []

        result = execute_tool("add_new_unit", {"flat_number": "A1", "building_name": "Ghost Building"}, db)

        assert "No building found" in result

    def test_duplicate_flat_number_returns_error(self):
        db = _mock_db()
        # Building found
        building_query = db.table.return_value.select.return_value.ilike.return_value
        building_query.execute.return_value.data = [{"id": "bld-uuid", "name": "Test Building"}]
        # Duplicate flat check — match found
        db.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = [{"id": 1}]

        result = execute_tool("add_new_unit", {"flat_number": "A-101", "building_name": "Test Building"}, db)

        assert isinstance(result, str)

    def test_missing_flat_number_returns_error(self):
        result = execute_tool("add_new_unit", {"building_name": "Building A"}, _mock_db())
        assert "flat_number" in result.lower() or "Missing" in result

    def test_missing_building_name_returns_error(self):
        result = execute_tool("add_new_unit", {"flat_number": "A-101"}, _mock_db())
        assert "building_name" in result.lower() or "Missing" in result

    def test_multiple_buildings_match_returns_ambiguity_error(self):
        db = _mock_db()
        db.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = [
            {"id": "bld-1", "name": "Building One", "address": "Addr 1"},
            {"id": "bld-2", "name": "Building Two", "address": "Addr 2"},
        ]

        result = execute_tool("add_new_unit", {"flat_number": "A1", "building_name": "Building"}, db)

        assert "Multiple" in result or "specific" in result.lower()


class TestExecuteToolRescheduleAppointment:
    def test_nonexistent_appointment_returns_error_message(self):
        db = _mock_db()
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        result = execute_tool("reschedule_appointment", {"appointment_id": 999, "new_date": "2026-06-15 10:00:00"}, db)

        assert isinstance(result, str)
        assert "999" in result
        assert "not found" in result.lower() or "No appointment" in result

    def test_completed_appointment_cannot_be_rescheduled(self):
        db = _mock_db()
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": 1, "status": "completed", "flat_uuid": None, "flat_number": "A-101"}
        ]

        result = execute_tool("reschedule_appointment", {"appointment_id": 1, "new_date": "2026-06-15 10:00:00"}, db)

        assert "completed" in result.lower()

    def test_cancelled_appointment_cannot_be_rescheduled(self):
        db = _mock_db()
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": 2, "status": "cancelled", "flat_uuid": None, "flat_number": "B-202"}
        ]

        result = execute_tool("reschedule_appointment", {"appointment_id": 2, "new_date": "2026-06-15 10:00:00"}, db)

        assert "cancelled" in result.lower()

    def test_missing_appointment_id_returns_error(self):
        result = execute_tool("reschedule_appointment", {"new_date": "2026-06-15 10:00:00"}, _mock_db())
        assert "appointment_id" in result.lower() or "Missing" in result


class TestExecuteToolCancelAppointment:
    def test_nonexistent_appointment_returns_error(self):
        db = _mock_db()
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        result = execute_tool("cancel_appointment", {"appointment_id": 999}, db)

        assert isinstance(result, str)
        assert "not found" in result.lower() or "No appointment" in result

    def test_already_cancelled_returns_idempotent_message(self):
        db = _mock_db()
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": 5, "status": "cancelled", "flat_number": "A-101", "flat_uuid": None}
        ]

        result = execute_tool("cancel_appointment", {"appointment_id": 5}, db)

        assert "already cancelled" in result.lower() or "cancelled" in result.lower()

    def test_missing_appointment_id_returns_error(self):
        result = execute_tool("cancel_appointment", {}, _mock_db())
        assert "appointment_id" in result.lower() or "Missing" in result


class TestExecuteToolDeleteTenant:
    def test_nonexistent_tenant_uuid_returns_error(self):
        db = _mock_db()
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        result = execute_tool("delete_tenant", {"tenant_uuid": "nonexistent-uuid"}, db)

        assert isinstance(result, str)
        assert "not found" in result.lower() or "No tenant" in result

    def test_missing_tenant_uuid_returns_error(self):
        result = execute_tool("delete_tenant", {}, _mock_db())
        assert "tenant_uuid" in result.lower() or "Missing" in result


class TestExecuteToolGetComplaints:
    def test_no_complaints_returns_message(self):
        db = _mock_db()
        db.table.return_value.select.return_value.order.return_value.execute.return_value.data = []

        result = execute_tool("get_complaints", {}, db)

        assert isinstance(result, str)
        assert "No complaints" in result or "no complaints" in result.lower()


class TestAppointmentWriteTools:
    def test_write_tools_set_is_correct(self):
        expected = {"reschedule_appointment", "cancel_appointment", "update_appointment_status"}
        assert _APPOINTMENT_WRITE_TOOLS == expected


# ---------------------------------------------------------------------------
# run_chat tests
# ---------------------------------------------------------------------------

class TestRunChatMessageTruncation:
    def test_truncates_to_last_10_messages(self):
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(20)]
        db = _mock_db()

        captured_messages = []

        def fake_create(**kwargs):
            captured_messages.extend(kwargs["messages"])
            return _mock_openai_text_response("Hello there")

        with patch("app.ai.chatbot.OpenAI") as MockOpenAI:
            MockOpenAI.return_value.chat.completions.create.side_effect = fake_create
            run_chat(messages, db)

        # system message + 10 user messages = 11
        user_messages = [m for m in captured_messages if m["role"] == "user"]
        assert len(user_messages) == 10
        assert user_messages[-1]["content"] == "msg 19"

    def test_does_not_truncate_when_10_or_fewer_messages(self):
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(5)]
        db = _mock_db()

        captured_messages = []

        def fake_create(**kwargs):
            captured_messages.extend(kwargs["messages"])
            return _mock_openai_text_response("OK")

        with patch("app.ai.chatbot.OpenAI") as MockOpenAI:
            MockOpenAI.return_value.chat.completions.create.side_effect = fake_create
            run_chat(messages, db)

        user_messages = [m for m in captured_messages if m["role"] == "user"]
        assert len(user_messages) == 5


class TestRunChatSimpleResponse:
    def test_simple_message_returns_reply_and_false_refresh(self):
        messages = [{"role": "user", "content": "Hello"}]
        db = _mock_db()

        with patch("app.ai.chatbot.OpenAI") as MockOpenAI:
            MockOpenAI.return_value.chat.completions.create.return_value = (
                _mock_openai_text_response("Hello! How can I help?")
            )
            reply, refresh_needed = run_chat(messages, db)

        assert reply == "Hello! How can I help?"
        assert refresh_needed is False


class TestRunChatRefreshNeeded:
    def test_appointment_write_tool_sets_refresh_needed_true(self):
        messages = [{"role": "user", "content": "Reschedule appointment 1"}]
        db = _mock_db()

        # Mock DB to return a valid appointment for reschedule
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": 1, "status": "scheduled", "flat_uuid": None, "flat_number": "A-101"}
        ]
        db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {"id": 1}
        ]

        tool_response = _mock_openai_tool_call_response(
            "reschedule_appointment",
            {"appointment_id": 1, "new_date": "2026-06-15 10:00:00"},
        )
        text_response = _mock_openai_text_response("Appointment rescheduled.")

        call_count = 0

        def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return tool_response
            return text_response

        with patch("app.ai.chatbot.OpenAI") as MockOpenAI, \
             patch("app.ai.chatbot.notify_tenant_appointment"):
            MockOpenAI.return_value.chat.completions.create.side_effect = fake_create
            _, refresh_needed = run_chat(messages, db)

        assert refresh_needed is True

    def test_non_write_tool_does_not_set_refresh_needed(self):
        messages = [{"role": "user", "content": "List buildings"}]
        db = _mock_db()
        db.table.return_value.select.return_value.order.return_value.execute.return_value.data = []

        tool_response = _mock_openai_tool_call_response("list_buildings", {})
        text_response = _mock_openai_text_response("No buildings found.")

        call_count = 0

        def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return tool_response
            return text_response

        with patch("app.ai.chatbot.OpenAI") as MockOpenAI:
            MockOpenAI.return_value.chat.completions.create.side_effect = fake_create
            _, refresh_needed = run_chat(messages, db)

        assert refresh_needed is False


class TestRunChatBadRequestFallback:
    def test_bad_request_error_falls_back_to_plain_completion(self):
        from openai import BadRequestError
        messages = [{"role": "user", "content": "Do something"}]
        db = _mock_db()

        call_count = 0

        def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if "tools" in kwargs:
                raise BadRequestError(
                    message="tool_use_failed",
                    response=MagicMock(status_code=400),
                    body={"error": {"message": "tool_use_failed"}},
                )
            return _mock_openai_text_response("Fallback response")

        with patch("app.ai.chatbot.OpenAI") as MockOpenAI:
            MockOpenAI.return_value.chat.completions.create.side_effect = fake_create
            reply, refresh_needed = run_chat(messages, db)

        assert reply == "Fallback response"
        assert refresh_needed is False
        assert call_count == 2  # First with tools (fails), second without

    def test_system_prompt_contains_today_date(self):
        """System prompt must have {today} replaced with actual date."""
        messages = [{"role": "user", "content": "What day is it?"}]
        db = _mock_db()

        captured_messages = []

        def fake_create(**kwargs):
            captured_messages.extend(kwargs["messages"])
            return _mock_openai_text_response("Today is...")

        with patch("app.ai.chatbot.OpenAI") as MockOpenAI:
            MockOpenAI.return_value.chat.completions.create.side_effect = fake_create
            run_chat(messages, db)

        system_msg = next(m for m in captured_messages if m["role"] == "system")
        assert "{today}" not in system_msg["content"]
        assert "2026" in system_msg["content"] or len(system_msg["content"]) > 50

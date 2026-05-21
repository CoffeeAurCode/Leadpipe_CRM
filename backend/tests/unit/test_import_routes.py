"""
Unit + endpoint tests for smart CSV/XLSX import routes.
Pure-function tests require no mocking. Endpoint tests override auth/DB dependencies.
"""
import io
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

import openpyxl

from app.routes.import_routes import (
    router,
    _parse_csv,
    _parse_xlsx,
    _detect_and_parse,
    _apply_mapping,
    _map_columns_with_ai,
)
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription

# ── Shared helpers ────────────────────────────────────────────────────────────

FAKE_USER = {"sub": "test-user-uuid"}


def _make_xlsx(headers: list, rows: list) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_db_for_properties() -> MagicMock:
    """DB mock: all selects → no existing records, all inserts → return IDs."""
    def _table(name):
        m = MagicMock()
        if name == "properties_list":
            m.select.return_value.ilike.return_value.execute.return_value.data = []
            m.insert.return_value.execute.return_value.data = [{"id": "prop-uuid"}]
        elif name == "buildings":
            m.select.return_value.eq.return_value.ilike.return_value.execute.return_value.data = []
            m.insert.return_value.execute.return_value.data = [{"id": 1}]
        elif name == "flats":
            m.select.return_value.ilike.return_value.execute.return_value.data = []
            m.insert.return_value.execute.return_value.data = [{"uuid": "flat-uuid"}]
        return m
    db = MagicMock()
    db.table.side_effect = _table
    return db


def _make_db_for_tenants() -> MagicMock:
    """DB mock: flat exists + is vacant, tenant insert succeeds."""
    def _table(name):
        m = MagicMock()
        if name == "flats":
            m.select.return_value.ilike.return_value.execute.return_value.data = [
                {"uuid": "flat-uuid", "tenant_uuid": None}
            ]
            m.update.return_value.eq.return_value.execute.return_value.data = []
        elif name == "tenants":
            m.insert.return_value.execute.return_value.data = [{"uuid": "tenant-uuid"}]
        elif name == "rents":
            m.insert.return_value.execute.return_value.data = [{"id": 1}]
        return m
    db = MagicMock()
    db.table.side_effect = _table
    return db


def _build_app(db_factory) -> tuple[FastAPI, MagicMock]:
    db = db_factory()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[require_active_subscription] = lambda: FAKE_USER
    app.dependency_overrides[get_authenticated_db] = lambda: db
    return app, db


# ── _parse_csv ────────────────────────────────────────────────────────────────

class TestParseCsv:
    def test_basic_parse(self):
        rows, fields = _parse_csv(b"property_name,building_name,flat_number\nSunrise,Block A,A-101\n")
        assert fields == {"property_name", "building_name", "flat_number"}
        assert rows == [{"property_name": "Sunrise", "building_name": "Block A", "flat_number": "A-101"}]

    def test_bom_prefix_stripped(self):
        bom = b"\xef\xbb\xbfproperty_name,building_name,flat_number\nSunrise,Block A,A-101\n"
        _, fields = _parse_csv(bom)
        assert "property_name" in fields

    def test_headers_lowercased(self):
        _, fields = _parse_csv(b"Property_Name,Building_Name,Flat_Number\nSunrise,Block A,A-101\n")
        assert "property_name" in fields
        assert "Property_Name" not in fields

    def test_values_and_headers_stripped(self):
        rows, _ = _parse_csv(b" property_name , flat_number \n Sunrise , A-101 \n")
        assert rows[0]["property_name"] == "Sunrise"
        assert rows[0]["flat_number"] == "A-101"

    def test_empty_csv_returns_empty_rows(self):
        rows, fields = _parse_csv(b"property_name,building_name,flat_number\n")
        assert rows == []
        assert "property_name" in fields

    def test_missing_value_becomes_empty_string(self):
        rows, _ = _parse_csv(b"name,phone,flat_number\nRahul,,A-101\n")
        assert rows[0]["phone"] == ""


# ── _parse_xlsx ───────────────────────────────────────────────────────────────

class TestParseXlsx:
    def test_basic_parse(self):
        content = _make_xlsx(
            ["property_name", "building_name", "flat_number"],
            [["Sunrise", "Block A", "A-101"]],
        )
        rows, fields = _parse_xlsx(content)
        assert "property_name" in fields
        assert rows[0]["flat_number"] == "A-101"

    def test_headers_lowercased(self):
        content = _make_xlsx(
            ["Property_Name", "Building_Name", "Flat_Number"],
            [["Sunrise", "Block A", "A-101"]],
        )
        _, fields = _parse_xlsx(content)
        assert "property_name" in fields
        assert "Property_Name" not in fields

    def test_empty_rows_skipped(self):
        content = _make_xlsx(
            ["property_name", "building_name", "flat_number"],
            [["Sunrise", "Block A", "A-101"], [None, None, None], ["Test", "Block B", "B-201"]],
        )
        rows, _ = _parse_xlsx(content)
        assert len(rows) == 2

    def test_header_only_sheet_returns_empty_rows(self):
        content = _make_xlsx(["property_name", "building_name", "flat_number"], [])
        rows, fields = _parse_xlsx(content)
        assert rows == []
        assert "property_name" in fields


# ── _detect_and_parse ─────────────────────────────────────────────────────────

class TestDetectAndParse:
    def test_csv_routed_by_filename(self):
        content = b"name,phone,flat_number\nRahul,+91987,A-101\n"
        rows, fields = _detect_and_parse(content, "tenants.csv")
        assert "name" in fields
        assert rows[0]["name"] == "Rahul"

    def test_xlsx_routed_by_filename(self):
        content = _make_xlsx(["name", "phone", "flat_number"], [["Rahul", "+91987", "A-101"]])
        rows, fields = _detect_and_parse(content, "tenants.xlsx")
        assert "name" in fields
        assert rows[0]["name"] == "Rahul"

    def test_extension_case_insensitive(self):
        content = b"name,phone,flat_number\nRahul,+91987,A-101\n"
        rows, _ = _detect_and_parse(content, "TENANTS.CSV")
        assert rows[0]["name"] == "Rahul"


# ── _apply_mapping ────────────────────────────────────────────────────────────

class TestApplyMapping:
    def test_renames_columns(self):
        rows = [{"tenant name": "Rahul", "mobile": "+91987", "unit no": "A-101"}]
        mapping = {"tenant name": "name", "mobile": "phone", "unit no": "flat_number"}
        assert _apply_mapping(rows, mapping) == [{"name": "Rahul", "phone": "+91987", "flat_number": "A-101"}]

    def test_null_target_drops_column(self):
        rows = [{"name": "Rahul", "extra": "discard"}]
        mapping = {"name": "name", "extra": None}
        result = _apply_mapping(rows, mapping)
        assert result == [{"name": "Rahul"}]

    def test_column_absent_from_mapping_dropped(self):
        rows = [{"col_a": "val_a", "col_b": "val_b"}]
        mapping = {"col_a": "name"}
        result = _apply_mapping(rows, mapping)
        assert "col_b" not in result[0]

    def test_empty_rows_and_mapping(self):
        assert _apply_mapping([], {}) == []

    def test_multiple_rows_all_mapped(self):
        rows = [{"a": "1"}, {"a": "2"}]
        result = _apply_mapping(rows, {"a": "name"})
        assert [r["name"] for r in result] == ["1", "2"]


# ── _map_columns_with_ai ──────────────────────────────────────────────────────

class TestMapColumnsWithAi:
    def _mock_client(self, response_json: dict) -> AsyncMock:
        resp = MagicMock()
        resp.choices[0].message.content = json.dumps(response_json)
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=resp)
        return client

    @pytest.mark.asyncio
    async def test_returns_valid_mapping(self):
        ai_reply = {"tenant name": "name", "mobile": "phone", "unit no": "flat_number", "extra": None}
        with patch("app.routes.import_routes.AsyncOpenAI", return_value=self._mock_client(ai_reply)):
            result = await _map_columns_with_ai(
                ["tenant name", "mobile", "unit no", "extra"],
                [{"tenant name": "Rahul"}],
                "tenants",
            )
        assert result["tenant name"] == "name"
        assert result["mobile"] == "phone"
        assert result["unit no"] == "flat_number"
        assert result["extra"] is None

    @pytest.mark.asyncio
    async def test_sanitizes_unknown_target_column(self):
        ai_reply = {"col_a": "not_a_real_column", "col_b": "name"}
        with patch("app.routes.import_routes.AsyncOpenAI", return_value=self._mock_client(ai_reply)):
            result = await _map_columns_with_ai(["col_a", "col_b"], [], "tenants")
        assert result["col_a"] is None
        assert result["col_b"] == "name"

    @pytest.mark.asyncio
    async def test_fills_headers_missing_from_ai_response(self):
        # OpenAI only maps col_a; col_b is absent from its response
        ai_reply = {"col_a": "name"}
        with patch("app.routes.import_routes.AsyncOpenAI", return_value=self._mock_client(ai_reply)):
            result = await _map_columns_with_ai(["col_a", "col_b"], [], "tenants")
        assert "col_b" in result
        assert result["col_b"] is None

    @pytest.mark.asyncio
    async def test_falls_back_all_null_on_openai_exception(self):
        bad_client = AsyncMock()
        bad_client.chat.completions.create = AsyncMock(side_effect=Exception("API down"))
        with patch("app.routes.import_routes.AsyncOpenAI", return_value=bad_client):
            result = await _map_columns_with_ai(["col_a", "col_b"], [], "properties")
        assert result == {"col_a": None, "col_b": None}

    @pytest.mark.asyncio
    async def test_falls_back_all_null_on_bad_json(self):
        resp = MagicMock()
        resp.choices[0].message.content = "not json {{{"
        bad_client = AsyncMock()
        bad_client.chat.completions.create = AsyncMock(return_value=resp)
        with patch("app.routes.import_routes.AsyncOpenAI", return_value=bad_client):
            result = await _map_columns_with_ai(["col_a"], [], "tenants")
        assert result == {"col_a": None}


# ── POST /import/analyze ──────────────────────────────────────────────────────

class TestAnalyzeEndpoint:
    def setup_method(self):
        app, _ = _build_app(_make_db_for_properties)
        self.client = TestClient(app)

    def _post(self, csv_bytes: bytes, import_type: str, filename: str = "t.csv"):
        return self.client.post(
            "/import/analyze",
            files={"file": (filename, io.BytesIO(csv_bytes), "text/csv")},
            data={"import_type": import_type},
        )

    def test_matching_properties_csv_needs_no_mapping(self):
        r = self._post(b"property_name,building_name,flat_number\nSunrise,Block A,A-101\n", "properties")
        assert r.status_code == 200
        assert r.json()["needs_mapping"] is False

    def test_matching_tenants_csv_needs_no_mapping(self):
        r = self._post(b"name,phone,flat_number\nRahul,+91987,A-101\n", "tenants")
        assert r.status_code == 200
        assert r.json()["needs_mapping"] is False

    def test_row_count_returned(self):
        r = self._post(
            b"property_name,building_name,flat_number\nSunrise,Block A,A-101\nSunrise,Block A,A-102\n",
            "properties",
        )
        assert r.json()["row_count"] == 2

    def test_non_matching_columns_triggers_ai_and_returns_mapping(self):
        ai_mapping = {"tenant name": "name", "mobile": "phone", "unit no": "flat_number"}
        with patch("app.routes.import_routes._map_columns_with_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = ai_mapping
            r = self._post(b"Tenant Name,Mobile,Unit No\nRahul,+91987,A-101\n", "tenants")
        assert r.status_code == 200
        body = r.json()
        assert body["needs_mapping"] is True
        assert body["mapping"] == ai_mapping
        assert body["unmapped_required"] == []

    def test_unmapped_required_columns_listed(self):
        ai_mapping = {"somecol": None, "anothercol": None}
        with patch("app.routes.import_routes._map_columns_with_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = ai_mapping
            r = self._post(b"somecol,anothercol\nv1,v2\n", "tenants")
        body = r.json()
        assert set(body["unmapped_required"]) == {"name", "phone", "flat_number"}

    def test_invalid_import_type_returns_400(self):
        r = self._post(b"col\nval\n", "not_valid")
        assert r.status_code == 400

    def test_file_too_large_returns_400(self):
        r = self._post(b"x" * (5 * 1024 * 1024 + 1), "properties")
        assert r.status_code == 400

    def test_xlsx_with_matching_columns_needs_no_mapping(self):
        xlsx = _make_xlsx(
            ["property_name", "building_name", "flat_number"],
            [["Sunrise", "Block A", "A-101"]],
        )
        r = self.client.post(
            "/import/analyze",
            files={"file": ("t.xlsx", io.BytesIO(xlsx), "application/vnd.ms-excel")},
            data={"import_type": "properties"},
        )
        assert r.status_code == 200
        assert r.json()["needs_mapping"] is False


# ── POST /import/properties (column_mapping parameter) ───────────────────────

class TestImportPropertiesMapping:
    def setup_method(self):
        app, _ = _build_app(_make_db_for_properties)
        self.client = TestClient(app)

    def test_non_standard_columns_without_mapping_returns_400(self):
        csv = b"prop,block,unit\nSunrise,Block A,A-101\n"
        r = self.client.post("/import/properties", files={"file": ("t.csv", io.BytesIO(csv), "text/csv")})
        assert r.status_code == 400
        assert "flat_number" in r.text or "missing" in r.text.lower()

    def test_non_standard_columns_with_valid_mapping_succeeds(self):
        csv = b"prop,block,unit\nSunrise,Block A,A-101\n"
        mapping = json.dumps({"prop": "property_name", "block": "building_name", "unit": "flat_number"})
        r = self.client.post(
            "/import/properties",
            files={"file": ("t.csv", io.BytesIO(csv), "text/csv")},
            data={"column_mapping": mapping},
        )
        assert r.status_code == 200
        body = r.json()
        assert "created" in body
        assert "skipped" in body
        assert "errors" in body

    def test_invalid_mapping_json_returns_400(self):
        csv = b"property_name,building_name,flat_number\nSunrise,Block A,A-101\n"
        r = self.client.post(
            "/import/properties",
            files={"file": ("t.csv", io.BytesIO(csv), "text/csv")},
            data={"column_mapping": "not-json{"},
        )
        assert r.status_code == 400

    def test_xlsx_with_standard_columns_succeeds(self):
        xlsx = _make_xlsx(["property_name", "building_name", "flat_number"], [["Sunrise", "Block A", "A-101"]])
        r = self.client.post(
            "/import/properties",
            files={"file": ("t.xlsx", io.BytesIO(xlsx), "application/vnd.ms-excel")},
        )
        assert r.status_code == 200


# ── POST /import/tenants (column_mapping parameter) ──────────────────────────

class TestImportTenantsMapping:
    def setup_method(self):
        app, _ = _build_app(_make_db_for_tenants)
        self.client = TestClient(app)

    def test_non_standard_columns_without_mapping_returns_400(self):
        csv = b"full_name,mobile,unit\nRahul,+91987,A-101\n"
        r = self.client.post("/import/tenants", files={"file": ("t.csv", io.BytesIO(csv), "text/csv")})
        assert r.status_code == 400

    def test_non_standard_columns_with_valid_mapping_succeeds(self):
        csv = b"full_name,mobile,unit\nRahul,+91987,A-101\n"
        mapping = json.dumps({"full_name": "name", "mobile": "phone", "unit": "flat_number"})
        r = self.client.post(
            "/import/tenants",
            files={"file": ("t.csv", io.BytesIO(csv), "text/csv")},
            data={"column_mapping": mapping},
        )
        assert r.status_code == 200
        body = r.json()
        assert "created" in body
        assert "errors" in body

    def test_xlsx_with_standard_columns_succeeds(self):
        xlsx = _make_xlsx(["name", "phone", "flat_number"], [["Rahul", "+91987", "A-101"]])
        r = self.client.post(
            "/import/tenants",
            files={"file": ("t.xlsx", io.BytesIO(xlsx), "application/vnd.ms-excel")},
        )
        assert r.status_code == 200

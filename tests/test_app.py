"""Unit tests for the Texto2Sql service.

All external I/O (OpenAI API, database connections) is mocked so the tests
run without any live services.
"""

import datetime
import decimal
import json
import unittest
from unittest.mock import MagicMock, patch

from app.llm.session_manager import SessionManager
from app.main import create_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(sm: SessionManager | None = None):
    app = create_app(session_manager=sm)
    app.config["TESTING"] = True
    return app.test_client()


_VALID_PAYLOAD = {
    "db_host": "localhost",
    "db_user": "user",
    "db_password": "secret",
    "db_port": 5432,
    "db_name": "testdb",
    "db_model": "postgres",
    "query_natural": "Show all users",
}


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class TestHealth(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_health_returns_200(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "ok")


# ---------------------------------------------------------------------------
# /query – input validation
# ---------------------------------------------------------------------------


class TestQueryValidation(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_empty_body_returns_400(self):
        resp = self.client.post("/query", data="", content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_non_json_body_returns_400(self):
        resp = self.client.post(
            "/query", data="not-json", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_missing_required_fields_returns_400(self):
        resp = self.client.post("/query", json={"db_host": "localhost"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Missing required fields", resp.get_json()["error"])

    def test_invalid_db_model_returns_400(self):
        payload = dict(_VALID_PAYLOAD, db_model="oracle")
        resp = self.client.post("/query", json=payload)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid db_model", resp.get_json()["error"])

    def test_valid_db_models_accepted(self):
        """All documented db_model values should pass validation (DB step will fail here)."""
        for model in ("mysql", "mariadb", "sqlsrv", "sybase", "postgres", "sqlite"):
            payload = dict(_VALID_PAYLOAD, db_model=model)
            # We only check that the 400 'Invalid db_model' error is NOT raised.
            # The request will still fail at the DB step (503), which is fine.
            with patch("app.main.create_engine"), patch(
                "app.main.get_schema", side_effect=Exception("db error")
            ):
                resp = self.client.post("/query", json=payload)
                self.assertNotEqual(resp.status_code, 400, f"Model {model!r} rejected")


# ---------------------------------------------------------------------------
# /query – successful flow (all external calls mocked)
# ---------------------------------------------------------------------------


class TestQuerySuccess(unittest.TestCase):
    def setUp(self):
        self.sm = SessionManager()
        self.client = _make_client(self.sm)

    @patch("app.main.execute_query")
    @patch("app.main.generate_sql")
    @patch("app.main.refine_query")
    @patch("app.main.get_schema")
    @patch("app.main.create_engine")
    def test_returns_columns_and_rows(
        self, mock_engine, mock_schema, mock_refine, mock_sql, mock_exec
    ):
        mock_schema.return_value = "TABLE users (id integer, name varchar)"
        mock_refine.return_value = "Retrieve all users"
        mock_sql.return_value = "SELECT id, name FROM users"
        mock_exec.return_value = {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "varchar"},
            ],
            "rows": [[1, "Alice"], [2, "Bob"]],
        }

        resp = self.client.post("/query", json=_VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("columns", data)
        self.assertIn("rows", data)
        self.assertIn("session_id", data)
        self.assertEqual(len(data["columns"]), 2)
        self.assertEqual(len(data["rows"]), 2)

    @patch("app.main.execute_query")
    @patch("app.main.generate_sql")
    @patch("app.main.refine_query")
    @patch("app.main.get_schema")
    @patch("app.main.create_engine")
    def test_session_id_echoed_when_provided(
        self, mock_engine, mock_schema, mock_refine, mock_sql, mock_exec
    ):
        mock_schema.return_value = ""
        mock_refine.return_value = "desc"
        mock_sql.return_value = "SELECT 1"
        mock_exec.return_value = {"columns": [], "rows": []}

        sid = "my-session-42"
        resp = self.client.post("/query", json=dict(_VALID_PAYLOAD, session_id=sid))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["session_id"], sid)

    @patch("app.main.execute_query")
    @patch("app.main.generate_sql")
    @patch("app.main.refine_query")
    @patch("app.main.get_schema")
    @patch("app.main.create_engine")
    def test_new_session_id_generated_when_absent(
        self, mock_engine, mock_schema, mock_refine, mock_sql, mock_exec
    ):
        mock_schema.return_value = ""
        mock_refine.return_value = "desc"
        mock_sql.return_value = "SELECT 1"
        mock_exec.return_value = {"columns": [], "rows": []}

        resp = self.client.post("/query", json=_VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 200)
        sid = resp.get_json()["session_id"]
        self.assertTrue(sid, "session_id should not be empty")


# ---------------------------------------------------------------------------
# /query – error propagation
# ---------------------------------------------------------------------------


class TestQueryErrors(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    @patch("app.main.create_engine")
    @patch("app.main.get_schema", side_effect=Exception("connection refused"))
    def test_db_error_returns_503(self, _mock_schema, _mock_engine):
        resp = self.client.post("/query", json=_VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 503)

    @patch("app.main.execute_query")
    @patch("app.main.generate_sql", side_effect=Exception("LLM unavailable"))
    @patch("app.main.refine_query")
    @patch("app.main.get_schema")
    @patch("app.main.create_engine")
    def test_llm_error_returns_503(
        self, _eng, _schema, _refine, _sql, _exec
    ):
        _schema.return_value = ""
        _refine.return_value = "desc"
        resp = self.client.post("/query", json=_VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 503)

    @patch("app.main.execute_query", side_effect=Exception("syntax error"))
    @patch("app.main.generate_sql")
    @patch("app.main.refine_query")
    @patch("app.main.get_schema")
    @patch("app.main.create_engine")
    def test_sql_error_returns_500(
        self, _eng, _schema, _refine, _sql, _exec
    ):
        _schema.return_value = ""
        _refine.return_value = "desc"
        _sql.return_value = "BAD SQL"
        resp = self.client.post("/query", json=_VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 500)


# ---------------------------------------------------------------------------
# /session/<id> DELETE
# ---------------------------------------------------------------------------


class TestDeleteSession(unittest.TestCase):
    def setUp(self):
        self.sm = SessionManager()
        self.client = _make_client(self.sm)

    def test_delete_nonexistent_returns_404(self):
        resp = self.client.delete("/session/does-not-exist")
        self.assertEqual(resp.status_code, 404)

    def test_delete_existing_returns_200(self):
        sid = "to-delete"
        self.sm.set_history(sid, "refiner", [{"role": "user", "content": "hi"}])
        resp = self.client.delete(f"/session/{sid}")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(self.sm.session_exists(sid))


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        self.sm = SessionManager()

    def test_empty_history_returns_empty_list(self):
        self.assertEqual(self.sm.get_history("new", "refiner"), [])

    def test_set_and_get_history(self):
        msgs = [{"role": "user", "content": "hello"}]
        self.sm.set_history("s1", "refiner", msgs)
        self.assertEqual(self.sm.get_history("s1", "refiner"), msgs)

    def test_get_returns_copy(self):
        self.sm.set_history("s2", "refiner", [])
        h = self.sm.get_history("s2", "refiner")
        h.append({"role": "user", "content": "injected"})
        self.assertEqual(self.sm.get_history("s2", "refiner"), [])

    def test_clear_existing_session(self):
        self.sm.set_history("s3", "refiner", [{"role": "user", "content": "x"}])
        self.assertTrue(self.sm.clear_session("s3"))
        self.assertFalse(self.sm.session_exists("s3"))

    def test_clear_nonexistent_session_returns_false(self):
        self.assertFalse(self.sm.clear_session("ghost"))

    def test_session_exists(self):
        self.assertFalse(self.sm.session_exists("no"))
        self.sm.set_history("yes", "refiner", [])
        self.assertTrue(self.sm.session_exists("yes"))

    def test_multiple_agents_are_independent(self):
        self.sm.set_history("s4", "refiner", [{"role": "user", "content": "a"}])
        self.sm.set_history("s4", "sql_agent", [{"role": "user", "content": "b"}])
        self.assertEqual(
            self.sm.get_history("s4", "refiner")[0]["content"], "a"
        )
        self.assertEqual(
            self.sm.get_history("s4", "sql_agent")[0]["content"], "b"
        )


# ---------------------------------------------------------------------------
# DB connector – URL builder
# ---------------------------------------------------------------------------


class TestBuildConnectionUrl(unittest.TestCase):
    def _build(self, model, **kwargs):
        from app.db.connector import build_connection_url

        defaults = {
            "db_host": "localhost",
            "db_user": "user",
            "db_password": "pass",
            "db_port": 3306,
            "db_name": "mydb",
        }
        defaults.update(kwargs)
        return build_connection_url(model, **defaults)

    def test_mysql_dialect(self):
        self.assertIn("mysql+pymysql", self._build("mysql"))

    def test_mariadb_uses_pymysql_dialect(self):
        self.assertIn("mysql+pymysql", self._build("mariadb"))

    def test_postgres_dialect(self):
        self.assertIn("postgresql+psycopg2", self._build("postgres", db_port=5432))

    def test_postgresql_alias(self):
        self.assertIn("postgresql+psycopg2", self._build("postgresql", db_port=5432))

    def test_sqlite_ignores_host_user_password(self):
        from app.db.connector import build_connection_url

        url = build_connection_url("sqlite", "", "", "", 0, "/tmp/test.db")
        self.assertEqual(url, "sqlite:////tmp/test.db")

    def test_sqlsrv_includes_driver(self):
        url = self._build("sqlsrv", db_port=1433)
        self.assertIn("mssql+pyodbc", url)
        self.assertIn("ODBC+Driver+17+for+SQL+Server", url)

    def test_unsupported_model_raises(self):
        from app.db.connector import build_connection_url

        with self.assertRaises(ValueError):
            build_connection_url("oracle", "h", "u", "p", 1521, "db")

    def test_special_chars_in_password_are_encoded(self):
        url = self._build("mysql", db_password="p@ss!w0rd#")
        self.assertNotIn("p@ss!w0rd#", url)

    def test_case_insensitive_model(self):
        self.assertIn("mysql+pymysql", self._build("MySQL"))


# ---------------------------------------------------------------------------
# DB connector – type mapping
# ---------------------------------------------------------------------------


class TestValueToSqlType(unittest.TestCase):
    def _t(self, val):
        from app.db.connector import _value_to_sql_type

        return _value_to_sql_type(val)

    def test_none(self):
        self.assertEqual(self._t(None), "unknown")

    def test_int(self):
        self.assertEqual(self._t(42), "integer")

    def test_bool_not_integer(self):
        # bool is a subclass of int – must resolve to "boolean"
        self.assertEqual(self._t(True), "boolean")
        self.assertEqual(self._t(False), "boolean")

    def test_float(self):
        self.assertEqual(self._t(3.14), "float")

    def test_decimal(self):
        self.assertEqual(self._t(decimal.Decimal("9.99")), "decimal")

    def test_str(self):
        self.assertEqual(self._t("hello"), "varchar")

    def test_bytes(self):
        self.assertEqual(self._t(b"data"), "binary")

    def test_date(self):
        self.assertEqual(self._t(datetime.date(2024, 1, 1)), "date")

    def test_datetime_not_date(self):
        # datetime is a subclass of date – must resolve to "datetime"
        self.assertEqual(
            self._t(datetime.datetime(2024, 1, 1, 12, 0, 0)), "datetime"
        )

    def test_time(self):
        self.assertEqual(self._t(datetime.time(12, 0, 0)), "time")


# ---------------------------------------------------------------------------
# DB connector – value serialisation
# ---------------------------------------------------------------------------


class TestSerializeValue(unittest.TestCase):
    def _s(self, val):
        from app.db.connector import _serialize_value

        return _serialize_value(val)

    def test_date_to_iso(self):
        self.assertEqual(self._s(datetime.date(2024, 6, 15)), "2024-06-15")

    def test_datetime_to_iso(self):
        self.assertEqual(
            self._s(datetime.datetime(2024, 6, 15, 10, 30, 0)), "2024-06-15T10:30:00"
        )

    def test_time_to_iso(self):
        self.assertEqual(self._s(datetime.time(8, 0, 0)), "08:00:00")

    def test_decimal_to_float(self):
        self.assertAlmostEqual(self._s(decimal.Decimal("3.14")), 3.14)

    def test_bytes_decoded(self):
        self.assertEqual(self._s(b"hello"), "hello")

    def test_passthrough_for_scalars(self):
        self.assertEqual(self._s(42), 42)
        self.assertEqual(self._s("text"), "text")
        self.assertIsNone(self._s(None))


# ---------------------------------------------------------------------------
# LLM converter – SQL cleaning
# ---------------------------------------------------------------------------


class TestCleanSql(unittest.TestCase):
    def _c(self, text):
        from app.llm.converter import _clean_sql

        return _clean_sql(text)

    def test_no_fences(self):
        self.assertEqual(self._c("SELECT 1"), "SELECT 1")

    def test_sql_fence(self):
        self.assertEqual(self._c("```sql\nSELECT 1\n```"), "SELECT 1")

    def test_generic_fence(self):
        self.assertEqual(self._c("```\nSELECT 1\n```"), "SELECT 1")

    def test_fence_without_newline(self):
        self.assertEqual(self._c("```sql SELECT 1```"), "SELECT 1")

    def test_leading_trailing_whitespace_stripped(self):
        self.assertEqual(self._c("  SELECT 1  "), "SELECT 1")


# ---------------------------------------------------------------------------
# LLM converter – agent functions (OpenAI mocked)
# ---------------------------------------------------------------------------


class TestConverterAgents(unittest.TestCase):
    def _mock_response(self, content: str):
        msg = MagicMock()
        msg.content = content
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    @patch("app.llm.converter._get_client")
    def test_refine_query_appends_history(self, mock_get_client):
        from app.llm.converter import refine_query

        sm = SessionManager()
        client = MagicMock()
        client.chat.completions.create.return_value = self._mock_response(
            "Retrieve all users"
        )
        mock_get_client.return_value = client

        result = refine_query("s1", "show users", "TABLE users (...)", sm)

        self.assertEqual(result, "Retrieve all users")
        history = sm.get_history("s1", "refiner")
        # system + user + assistant
        self.assertEqual(len(history), 3)
        self.assertEqual(history[1]["role"], "user")
        self.assertEqual(history[2]["role"], "assistant")

    @patch("app.llm.converter._get_client")
    def test_generate_sql_strips_fences(self, mock_get_client):
        from app.llm.converter import generate_sql

        sm = SessionManager()
        client = MagicMock()
        client.chat.completions.create.return_value = self._mock_response(
            "```sql\nSELECT * FROM users\n```"
        )
        mock_get_client.return_value = client

        sql = generate_sql("s2", "Get all users", "TABLE users (...)", "postgres", sm)

        self.assertEqual(sql, "SELECT * FROM users")

    @patch("app.llm.converter._get_client")
    def test_session_continuity_across_calls(self, mock_get_client):
        from app.llm.converter import refine_query

        sm = SessionManager()
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            self._mock_response("First refined"),
            self._mock_response("Second refined"),
        ]
        mock_get_client.return_value = client

        refine_query("s3", "question 1", "schema", sm)
        refine_query("s3", "question 2", "schema", sm)

        history = sm.get_history("s3", "refiner")
        # system + (user + assistant) × 2 = 5 messages
        self.assertEqual(len(history), 5)


if __name__ == "__main__":
    unittest.main()

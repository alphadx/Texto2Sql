"""Unit tests for the Texto2Sql service.

All external I/O (OpenAI API, database connections) is mocked so the tests
run without any live services.
"""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.llm.session_manager import SessionManager
from app.main import create_app


def _make_client(sm: SessionManager | None = None):
    app = create_app(session_manager=sm)
    return TestClient(app)


_VALID_PAYLOAD = {
    "host": "localhost",
    "usuario": "user",
    "contraseña": "secret",
    "puerto": 5432,
    "nombre_bd": "testdb",
    "motor_bd": "postgres",
    "consulta_nl": "Show all users",
}


class TestHealth(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_health_returns_200(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")


class TestQueryValidation(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_empty_body_returns_422(self):
        resp = self.client.post("/nl2sql/query", data="", headers={"content-type": "application/json"})
        self.assertEqual(resp.status_code, 422)

    def test_non_json_body_returns_422(self):
        resp = self.client.post(
            "/nl2sql/query", data="not-json", headers={"content-type": "application/json"}
        )
        self.assertEqual(resp.status_code, 422)

    def test_missing_required_fields_returns_422(self):
        resp = self.client.post("/nl2sql/query", json={"host": "localhost"})
        self.assertEqual(resp.status_code, 422)

    def test_valid_db_models_accepted(self):
        for model in ("mysql", "mariadb", "sqlsrv", "sybase", "postgres", "sqlite"):
            payload = dict(_VALID_PAYLOAD, motor_bd=model)
            with patch("app.api.create_engine"), patch(
                "app.api.get_schema", side_effect=Exception("db error")
            ):
                resp = self.client.post("/nl2sql/query", json=payload)
                self.assertNotEqual(resp.status_code, 422, f"Model {model!r} rejected")


class TestQuerySuccess(unittest.TestCase):
    def setUp(self):
        self.sm = SessionManager()
        self.client = _make_client(self.sm)

    @patch("app.api.execute_query")
    @patch("app.api.generate_sql")
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_returns_columns_and_rows(
        self, _mock_engine, mock_schema, mock_refine, mock_sql, mock_exec
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

        resp = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("columns", data)
        self.assertIn("rows", data)
        self.assertIn("session_id", data)

    @patch("app.api.execute_query")
    @patch("app.api.generate_sql")
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_session_id_echoed_when_provided(
        self, _mock_engine, mock_schema, mock_refine, mock_sql, mock_exec
    ):
        mock_schema.return_value = ""
        mock_refine.return_value = "desc"
        mock_sql.return_value = "SELECT 1"
        mock_exec.return_value = {"columns": [], "rows": []}

        sid = "my-session-42"
        resp = self.client.post("/nl2sql/query", json=dict(_VALID_PAYLOAD, session_id=sid))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["session_id"], sid)

    @patch("app.api.execute_query")
    @patch("app.api.generate_sql")
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_new_session_id_generated_when_absent(
        self, _mock_engine, mock_schema, mock_refine, mock_sql, mock_exec
    ):
        mock_schema.return_value = ""
        mock_refine.return_value = "desc"
        mock_sql.return_value = "SELECT 1"
        mock_exec.return_value = {"columns": [], "rows": []}

        resp = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 200)
        sid = resp.json()["session_id"]
        self.assertTrue(sid)


class TestQueryErrors(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    @patch("app.api.create_engine")
    @patch("app.api.get_schema", side_effect=Exception("connection refused"))
    def test_db_error_returns_503(self, _mock_schema, _mock_engine):
        resp = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 503)

    @patch("app.api.execute_query")
    @patch("app.api.generate_sql", side_effect=Exception("LLM unavailable"))
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_llm_error_returns_503(self, _eng, _schema, _refine, _sql, _exec):
        _schema.return_value = ""
        _refine.return_value = "desc"
        resp = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 503)

    @patch("app.api.execute_query", side_effect=Exception("syntax error"))
    @patch("app.api.generate_sql")
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_sql_error_returns_500(self, _eng, _schema, _refine, _sql, _exec):
        _schema.return_value = ""
        _refine.return_value = "desc"
        _sql.return_value = "SELECT * FROM users"
        resp = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 500)

    @patch("app.api.execute_query")
    @patch("app.api.generate_sql")
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_non_select_sql_returns_400(self, _eng, _schema, _refine, _sql, _exec):
        _schema.return_value = ""
        _refine.return_value = "desc"
        _sql.return_value = "DELETE FROM users"

        resp = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 400)
        _exec.assert_not_called()


class TestSqlGuard(unittest.TestCase):
    def test_apply_limit_for_postgres_when_absent(self):
        from app.db.sql_guard import apply_row_limit

        sql = apply_row_limit("SELECT * FROM users", db_model="postgres", max_rows=100)
        self.assertEqual(sql, "SELECT * FROM users LIMIT 100")

    def test_apply_top_for_sqlsrv_when_absent(self):
        from app.db.sql_guard import apply_row_limit

        sql = apply_row_limit("SELECT DISTINCT id FROM users", db_model="sqlsrv", max_rows=50)
        self.assertEqual(sql, "SELECT DISTINCT TOP 50 id FROM users")

    def test_rejects_multiple_statements(self):
        from app.db.sql_guard import SQLValidationError, validate_sql_query

        with self.assertRaises(SQLValidationError):
            validate_sql_query("SELECT 1; SELECT 2")


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

    def test_clear_non_existing_session(self):
        self.assertFalse(self.sm.clear_session("nope"))


if __name__ == "__main__":
    unittest.main()

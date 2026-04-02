"""Unit tests for the Texto2Sql service.

All external I/O (OpenAI API, database connections) is mocked so the tests
run without any live services.
"""

import os
import threading
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt

os.environ.setdefault("AUTH_REQUIRED", "true")
os.environ.setdefault("AUTH_JWT_SECRET", "test-super-secret-key-for-jwt-signing-32chars")
os.environ.setdefault("AUTH_JWT_ALGORITHM", "HS256")

from app.llm import session_manager as sm_module

from fastapi.testclient import TestClient

from app.llm.session_manager import InMemorySessionManager, RedisSessionManager, build_session_manager_from_env
from app.main import create_app


def _make_client(sm=None):
    os.environ.update(_auth_env())
    app = create_app(session_manager=sm)
    return TestClient(app)


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.expiry = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value
        self.expiry[key] = ex
        return True

    def exists(self, key):
        return int(key in self.store)

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.store:
                deleted += 1
                del self.store[key]
                self.expiry.pop(key, None)
        return deleted

    def expire(self, key, seconds):
        if key not in self.store:
            return False
        self.expiry[key] = seconds
        return True






_TEST_AUTH_SECRET = "test-super-secret-key-for-jwt-signing-32chars"


def _auth_env():
    return {
        "AUTH_REQUIRED": "true",
        "AUTH_JWT_SECRET": _TEST_AUTH_SECRET,
        "AUTH_JWT_ALGORITHM": "HS256",
    }


def _build_token(*, scopes=None, roles=None, sub="test-user"):
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    if scopes is not None:
        payload["scopes"] = scopes
    if roles is not None:
        payload["roles"] = roles
    return jwt.encode(payload, _TEST_AUTH_SECRET, algorithm="HS256")


def _auth_headers(*, scopes=None, roles=None):
    return {"Authorization": f"Bearer {_build_token(scopes=scopes, roles=roles)}"}


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
        resp = self.client.post("/nl2sql/query", data="", headers={"content-type": "application/json", **_auth_headers(scopes=["query:execute"])})
        self.assertEqual(resp.status_code, 422)

    def test_non_json_body_returns_422(self):
        resp = self.client.post(
            "/nl2sql/query", data="not-json", headers={"content-type": "application/json", **_auth_headers(scopes=["query:execute"])}
        )
        self.assertEqual(resp.status_code, 422)

    def test_missing_required_fields_returns_422(self):
        resp = self.client.post("/nl2sql/query", json={"host": "localhost"}, headers=_auth_headers(scopes=["query:execute"]))
        self.assertEqual(resp.status_code, 422)

    def test_valid_db_models_accepted(self):
        for model in ("mysql", "mariadb", "sqlsrv", "sybase", "postgres", "sqlite"):
            payload = dict(_VALID_PAYLOAD, motor_bd=model)
            with patch("app.api.create_engine"), patch(
                "app.api.get_schema", side_effect=Exception("db error")
            ):
                resp = self.client.post("/nl2sql/query", json=payload, headers=_auth_headers(scopes=["query:execute"]))
                self.assertNotEqual(resp.status_code, 422, f"Model {model!r} rejected")


class TestQuerySuccess(unittest.TestCase):
    def setUp(self):
        self.sm = InMemorySessionManager()
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

        resp = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD, headers=_auth_headers(scopes=["query:execute"]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("columns", data)
        self.assertIn("rows", data)
        self.assertIn("session_id", data)
        self.assertEqual(data["texto_formal"], "Retrieve all users")

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
        resp = self.client.post("/nl2sql/query", json=dict(_VALID_PAYLOAD, session_id=sid), headers=_auth_headers(scopes=["query:execute"]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["session_id"], sid)


    @patch("app.api.execute_query")
    @patch("app.api.generate_sql")
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_llm_override_params_are_forwarded(
        self, _mock_engine, mock_schema, mock_refine, mock_sql, mock_exec
    ):
        mock_schema.return_value = ""
        mock_refine.return_value = "desc"
        mock_sql.return_value = "SELECT 1"
        mock_exec.return_value = {"columns": [], "rows": []}

        payload = dict(
            _VALID_PAYLOAD,
            llm_provider="anthropic",
            llm_model="claude-sonnet",
            llm_api_key="key-123",
            llm_base_url="https://example.test/v1",
        )

        resp = self.client.post("/nl2sql/query", json=payload, headers=_auth_headers(scopes=["query:execute"]))
        self.assertEqual(resp.status_code, 200)

        refine_opts = mock_refine.call_args.kwargs["llm_options"]
        sql_opts = mock_sql.call_args.kwargs["llm_options"]

        self.assertEqual(refine_opts["provider"], "anthropic")
        self.assertEqual(refine_opts["model"], "claude-sonnet")
        self.assertEqual(refine_opts["api_key"], "key-123")
        self.assertEqual(refine_opts["base_url"], "https://example.test/v1")
        self.assertEqual(sql_opts, refine_opts)

    @patch("app.api.execute_query")
    @patch("app.api.generate_sql")
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_huggingface_pipeline_options_are_forwarded_end_to_end(
        self, _mock_engine, mock_schema, mock_refine, mock_sql, mock_exec
    ):
        mock_schema.return_value = ""
        mock_refine.return_value = "desc"
        mock_sql.return_value = "SELECT 1"
        mock_exec.return_value = {"columns": [], "rows": []}

        payload = dict(
            _VALID_PAYLOAD,
            llm_provider="huggingface",
            llm_model="Qwen/Qwen2.5-3B-Instruct",
            llm_api_key="hf-key",
            llm_base_url="https://dedicated.hf.endpoint/v1",
        )

        resp = self.client.post("/nl2sql/query", json=payload, headers=_auth_headers(scopes=["query:execute"]))
        self.assertEqual(resp.status_code, 200)

        refine_opts = mock_refine.call_args.kwargs["llm_options"]
        sql_opts = mock_sql.call_args.kwargs["llm_options"]

        self.assertEqual(refine_opts["provider"], "huggingface")
        self.assertEqual(refine_opts["model"], "Qwen/Qwen2.5-3B-Instruct")
        self.assertEqual(refine_opts["api_key"], "hf-key")
        self.assertEqual(refine_opts["base_url"], "https://dedicated.hf.endpoint/v1")
        self.assertEqual(sql_opts, refine_opts)

    @patch("app.api.execute_query")
    @patch("app.api.generate_sql")
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_gemini_pipeline_options_are_forwarded_end_to_end(
        self, _mock_engine, mock_schema, mock_refine, mock_sql, mock_exec
    ):
        mock_schema.return_value = ""
        mock_refine.return_value = "desc"
        mock_sql.return_value = "SELECT 1"
        mock_exec.return_value = {"columns": [], "rows": []}

        payload = dict(
            _VALID_PAYLOAD,
            llm_provider="gemini",
            llm_model="gemini-2.0-flash-lite",
            llm_api_key="g-key",
            llm_base_url="https://generativelanguage.googleapis.com",
        )

        resp = self.client.post("/nl2sql/query", json=payload, headers=_auth_headers(scopes=["query:execute"]))
        self.assertEqual(resp.status_code, 200)

        refine_opts = mock_refine.call_args.kwargs["llm_options"]
        sql_opts = mock_sql.call_args.kwargs["llm_options"]

        self.assertEqual(refine_opts["provider"], "gemini")
        self.assertEqual(refine_opts["model"], "gemini-2.0-flash-lite")
        self.assertEqual(refine_opts["api_key"], "g-key")
        self.assertEqual(refine_opts["base_url"], "https://generativelanguage.googleapis.com")
        self.assertEqual(sql_opts, refine_opts)

    @patch("app.api.execute_query")
    @patch("app.api.generate_sql")
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_mistral_pipeline_options_are_forwarded_end_to_end(
        self, _mock_engine, mock_schema, mock_refine, mock_sql, mock_exec
    ):
        mock_schema.return_value = ""
        mock_refine.return_value = "desc"
        mock_sql.return_value = "SELECT 1"
        mock_exec.return_value = {"columns": [], "rows": []}

        payload = dict(
            _VALID_PAYLOAD,
            llm_provider="mistral",
            llm_model="mistral-small-latest",
            llm_api_key="m-key",
            llm_base_url="https://api.mistral.ai/v1",
        )

        resp = self.client.post("/nl2sql/query", json=payload, headers=_auth_headers(scopes=["query:execute"]))
        self.assertEqual(resp.status_code, 200)

        refine_opts = mock_refine.call_args.kwargs["llm_options"]
        sql_opts = mock_sql.call_args.kwargs["llm_options"]

        self.assertEqual(refine_opts["provider"], "mistral")
        self.assertEqual(refine_opts["model"], "mistral-small-latest")
        self.assertEqual(refine_opts["api_key"], "m-key")
        self.assertEqual(refine_opts["base_url"], "https://api.mistral.ai/v1")
        self.assertEqual(sql_opts, refine_opts)

    @patch("app.api.execute_query")
    @patch("app.api.generate_sql")
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_claude_pipeline_options_are_forwarded_end_to_end(
        self, _mock_engine, mock_schema, mock_refine, mock_sql, mock_exec
    ):
        mock_schema.return_value = ""
        mock_refine.return_value = "desc"
        mock_sql.return_value = "SELECT 1"
        mock_exec.return_value = {"columns": [], "rows": []}

        payload = dict(
            _VALID_PAYLOAD,
            llm_provider="claude",
            llm_model="claude-3-5-haiku-latest",
            llm_api_key="a-key",
            llm_base_url="https://api.anthropic.com",
        )

        resp = self.client.post("/nl2sql/query", json=payload, headers=_auth_headers(scopes=["query:execute"]))
        self.assertEqual(resp.status_code, 200)

        refine_opts = mock_refine.call_args.kwargs["llm_options"]
        sql_opts = mock_sql.call_args.kwargs["llm_options"]

        self.assertEqual(refine_opts["provider"], "claude")
        self.assertEqual(refine_opts["model"], "claude-3-5-haiku-latest")
        self.assertEqual(refine_opts["api_key"], "a-key")
        self.assertEqual(refine_opts["base_url"], "https://api.anthropic.com")
        self.assertEqual(sql_opts, refine_opts)

    @patch("app.api.execute_query")
    @patch("app.api.generate_sql")
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_llama_pipeline_options_are_forwarded_end_to_end(
        self, _mock_engine, mock_schema, mock_refine, mock_sql, mock_exec
    ):
        mock_schema.return_value = ""
        mock_refine.return_value = "desc"
        mock_sql.return_value = "SELECT 1"
        mock_exec.return_value = {"columns": [], "rows": []}

        payload = dict(
            _VALID_PAYLOAD,
            llm_provider="llama",
            llm_model="meta-llama/Llama-3.1-8B-Instruct",
            llm_api_key="l-key",
            llm_base_url="https://router.huggingface.co/v1",
        )

        resp = self.client.post("/nl2sql/query", json=payload, headers=_auth_headers(scopes=["query:execute"]))
        self.assertEqual(resp.status_code, 200)

        refine_opts = mock_refine.call_args.kwargs["llm_options"]
        sql_opts = mock_sql.call_args.kwargs["llm_options"]

        self.assertEqual(refine_opts["provider"], "llama")
        self.assertEqual(refine_opts["model"], "meta-llama/Llama-3.1-8B-Instruct")
        self.assertEqual(refine_opts["api_key"], "l-key")
        self.assertEqual(refine_opts["base_url"], "https://router.huggingface.co/v1")
        self.assertEqual(sql_opts, refine_opts)

    @patch("app.api.execute_query")
    @patch("app.api.generate_sql")
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_copilot_pipeline_options_are_forwarded_end_to_end(
        self, _mock_engine, mock_schema, mock_refine, mock_sql, mock_exec
    ):
        mock_schema.return_value = ""
        mock_refine.return_value = "desc"
        mock_sql.return_value = "SELECT 1"
        mock_exec.return_value = {"columns": [], "rows": []}

        payload = dict(
            _VALID_PAYLOAD,
            llm_provider="copilot",
            llm_model="gpt-4.1-mini",
            llm_api_key="c-key",
            llm_base_url="https://models.inference.ai.azure.com",
        )

        resp = self.client.post("/nl2sql/query", json=payload, headers=_auth_headers(scopes=["query:execute"]))
        self.assertEqual(resp.status_code, 200)

        refine_opts = mock_refine.call_args.kwargs["llm_options"]
        sql_opts = mock_sql.call_args.kwargs["llm_options"]

        self.assertEqual(refine_opts["provider"], "copilot")
        self.assertEqual(refine_opts["model"], "gpt-4.1-mini")
        self.assertEqual(refine_opts["api_key"], "c-key")
        self.assertEqual(refine_opts["base_url"], "https://models.inference.ai.azure.com")
        self.assertEqual(sql_opts, refine_opts)
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

        resp = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD, headers=_auth_headers(scopes=["query:execute"]))
        self.assertEqual(resp.status_code, 200)
        sid = resp.json()["session_id"]
        self.assertTrue(sid)


class TestQueryRegressionWithRedis(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.sm = RedisSessionManager(self.redis, ttl_seconds=120, key_prefix="test:session")
        self.client = _make_client(self.sm)

    @patch("app.api.execute_query")
    @patch("app.api.generate_sql")
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_nl2sql_query_flow_remains_ok_with_redis_session_manager(
        self, _mock_engine, mock_schema, mock_refine, mock_sql, mock_exec
    ):
        mock_schema.return_value = "TABLE users (id integer)"
        mock_refine.return_value = "Retrieve users"
        mock_sql.return_value = "SELECT id FROM users"
        mock_exec.return_value = {"columns": [{"name": "id", "type": "integer"}], "rows": [[1], [2]]}

        sid = "redis-regression-sid"
        payload = dict(_VALID_PAYLOAD, session_id=sid)
        resp = self.client.post("/nl2sql/query", json=payload, headers=_auth_headers(scopes=["query:execute"]))

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["session_id"], sid)
        self.assertEqual(body["columns"][0]["name"], "id")
        self.assertEqual(body["rows"], [[1], [2]])
        self.assertEqual(body["texto_formal"], "Retrieve users")
        mock_refine.assert_called_once()
        mock_sql.assert_called_once()
        mock_exec.assert_called_once()


class TestObservability(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    @patch("app.api._audit_logger.persist")
    @patch("app.api.execute_query")
    @patch("app.api.generate_sql")
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_audit_event_contains_required_fields(
        self, _mock_engine, mock_schema, mock_refine, mock_sql, mock_exec, mock_persist
    ):
        mock_schema.return_value = ""
        mock_refine.return_value = "desc"
        mock_sql.return_value = "SELECT 1"
        mock_exec.return_value = {"columns": [], "rows": []}

        payload = dict(_VALID_PAYLOAD, session_id="session-observability")
        resp = self.client.post("/nl2sql/query", json=payload, headers=_auth_headers(scopes=["query:execute"]))

        self.assertEqual(resp.status_code, 200)
        mock_persist.assert_called_once()
        event = mock_persist.call_args.args[0]
        self.assertEqual(event["session_id"], "session-observability")
        self.assertEqual(event["engine"], "postgres")
        self.assertEqual(event["status_code"], 200)
        self.assertIn("schema", event["durations_ms"])
        self.assertIn("llm", event["durations_ms"])
        self.assertIn("sql", event["durations_ms"])

    def test_metrics_endpoint_exposes_prometheus_format(self):
        resp = self.client.get("/metrics")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("nl2sql_requests_total", resp.text)
        self.assertIn("nl2sql_request_latency_ms_count", resp.text)
        self.assertIn("nl2sql_errors_total", resp.text)


class TestQueryErrors(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    @patch("app.api.create_engine")
    @patch("app.api.get_schema", side_effect=Exception("connection refused"))
    def test_db_error_returns_503(self, _mock_schema, _mock_engine):
        resp = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD, headers=_auth_headers(scopes=["query:execute"]))
        self.assertEqual(resp.status_code, 503)

    @patch("app.api.execute_query")
    @patch("app.api.generate_sql", side_effect=Exception("LLM unavailable"))
    @patch("app.api.refine_query")
    @patch("app.api.get_schema")
    @patch("app.api.create_engine")
    def test_llm_error_returns_503(self, _eng, _schema, _refine, _sql, _exec):
        _schema.return_value = ""
        _refine.return_value = "desc"
        resp = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD, headers=_auth_headers(scopes=["query:execute"]))
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
        resp = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD, headers=_auth_headers(scopes=["query:execute"]))
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

        resp = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD, headers=_auth_headers(scopes=["query:execute"]))
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
        self.sm = InMemorySessionManager()
        self.client = _make_client(self.sm)

    def test_delete_nonexistent_returns_404(self):
        resp = self.client.delete("/session/does-not-exist", headers=_auth_headers(roles=["admin"]))
        self.assertEqual(resp.status_code, 404)

    def test_delete_existing_returns_200(self):
        sid = "to-delete"
        self.sm.set_history(sid, "refiner", [{"role": "user", "content": "hi"}])
        resp = self.client.delete(f"/session/{sid}", headers=_auth_headers(roles=["admin"]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(self.sm.session_exists(sid))


class TestDeleteSessionRedis(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.sm = RedisSessionManager(self.redis, ttl_seconds=120, key_prefix="test:session")
        self.client = _make_client(self.sm)

    def test_delete_existing_redis_session_clears_both_agents(self):
        sid = "redis-delete-ok"
        self.sm.set_history(sid, "refiner", [{"role": "user", "content": "hola"}])
        self.sm.set_history(sid, "sql_agent", [{"role": "assistant", "content": "SELECT 1"}])

        self.assertIn(f"test:session:{sid}:refiner", self.redis.store)
        self.assertIn(f"test:session:{sid}:sql_agent", self.redis.store)

        resp = self.client.delete(f"/session/{sid}", headers=_auth_headers(roles=["admin"]))
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(f"test:session:{sid}:refiner", self.redis.store)
        self.assertNotIn(f"test:session:{sid}:sql_agent", self.redis.store)

    def test_delete_returns_404_when_session_expired_before_request(self):
        sid = "redis-delete-expired"
        self.sm.set_history(sid, "refiner", [{"role": "user", "content": "hola"}])

        # Simula expiración TTL justo antes de DELETE.
        self.redis.delete(f"test:session:{sid}:refiner", f"test:session:{sid}:sql_agent")

        resp = self.client.delete(f"/session/{sid}", headers=_auth_headers(roles=["admin"]))
        self.assertEqual(resp.status_code, 404)

    def test_delete_with_concurrent_writes_keeps_consistent_state(self):
        sid = "redis-delete-race"
        self.sm.set_history(sid, "refiner", [{"role": "user", "content": "seed"}])
        self.sm.set_history(sid, "sql_agent", [{"role": "assistant", "content": "SELECT 1"}])

        start = threading.Event()

        def writer():
            start.wait()
            for i in range(25):
                self.sm.set_history(sid, "refiner", [{"role": "user", "content": f"race-{i}"}])
                self.sm.set_history(sid, "sql_agent", [{"role": "assistant", "content": f"SELECT {i}"}])

        t = threading.Thread(target=writer)
        t.start()
        start.set()

        first_delete = self.client.delete(f"/session/{sid}", headers=_auth_headers(roles=["admin"]))
        self.assertEqual(first_delete.status_code, 200)

        t.join()

        # Según el interleaving, puede haberse recreado la sesión tras el primer delete.
        second_delete = self.client.delete(f"/session/{sid}", headers=_auth_headers(roles=["admin"]))
        self.assertIn(second_delete.status_code, (200, 404))
        if second_delete.status_code == 200:
            third_delete = self.client.delete(f"/session/{sid}", headers=_auth_headers(roles=["admin"]))
            self.assertEqual(third_delete.status_code, 404)


class TestAuth(unittest.TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_query_requires_bearer_token(self):
        resp = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD)
        self.assertEqual(resp.status_code, 401)

    def test_query_requires_scope(self):
        resp = self.client.post(
            "/nl2sql/query",
            json=_VALID_PAYLOAD,
            headers=_auth_headers(scopes=["other:scope"]),
        )
        self.assertEqual(resp.status_code, 403)

    def test_delete_session_requires_admin_scope_or_role(self):
        resp = self.client.delete("/session/not-found", headers=_auth_headers(scopes=["query:execute"]))
        self.assertEqual(resp.status_code, 403)


class TestSecurityStartupValidation(unittest.TestCase):
    def test_missing_secret_fails_startup(self):
        with patch.dict(os.environ, {"AUTH_REQUIRED": "true", "AUTH_JWT_SECRET": ""}, clear=False):
            with self.assertRaises(RuntimeError):
                create_app()

    def test_insecure_secret_fails_startup(self):
        with patch.dict(os.environ, {"AUTH_REQUIRED": "true", "AUTH_JWT_SECRET": "changeme"}, clear=False):
            with self.assertRaises(RuntimeError):
                create_app()


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        self.sm = InMemorySessionManager()

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

    def test_invalid_agent_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.sm.get_history("s4", "unknown-agent")


class TestRedisSessionManager(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.sm = RedisSessionManager(self.redis, ttl_seconds=120, key_prefix="test:session")

    def test_set_history_serializes_json_and_sets_ttl(self):
        sid = "redis-s1"
        history = [{"role": "user", "content": "hola"}]
        self.sm.set_history(sid, "refiner", history)

        redis_key = "test:session:redis-s1:refiner"
        self.assertIn(redis_key, self.redis.store)
        self.assertEqual(self.redis.expiry[redis_key], 120)
        self.assertEqual(self.sm.get_history(sid, "refiner"), history)

    def test_session_exists_and_clear_session(self):
        sid = "redis-s2"
        self.sm.set_history(sid, "refiner", [{"role": "user", "content": "q"}])
        self.assertTrue(self.sm.session_exists(sid))
        self.assertTrue(self.sm.clear_session(sid))
        self.assertFalse(self.sm.session_exists(sid))

    def test_invalid_json_payload_returns_empty_and_deletes_key(self):
        sid = "redis-s3"
        key = "test:session:redis-s3:refiner"
        self.redis.store[key] = "{invalid-json"

        history = self.sm.get_history(sid, "refiner")

        self.assertEqual(history, [])
        self.assertNotIn(key, self.redis.store)

    def test_invalid_agent_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.sm.set_history("s5", "unknown-agent", [])

    def test_sliding_ttl_renews_expiry_on_get(self):
        sid = "redis-s4"
        self.sm = RedisSessionManager(self.redis, ttl_seconds=30, key_prefix="test:session", sliding_ttl=True)
        self.sm.set_history(sid, "refiner", [{"role": "user", "content": "hola"}])

        key = "test:session:redis-s4:refiner"
        self.redis.expiry[key] = 5

        history = self.sm.get_history(sid, "refiner")
        self.assertEqual(history, [{"role": "user", "content": "hola"}])
        self.assertEqual(self.redis.expiry[key], 30)


class TestSessionManagerEnvFactory(unittest.TestCase):
    @patch.object(sm_module.Redis, "from_url")
    @patch.dict("os.environ", {
        "SESSION_MANAGER_BACKEND": "redis",
        "REDIS_URL": "redis://cache:6379/2",
        "SESSION_TTL_SECONDS": "1800",
        "SESSION_KEY_PREFIX": "my:prefix",
    }, clear=False)
    def test_build_redis_manager_from_env(self, mock_from_url):
        fake_client = FakeRedis()
        mock_from_url.return_value = fake_client

        manager = build_session_manager_from_env()

        self.assertIsInstance(manager, RedisSessionManager)
        mock_from_url.assert_called_once_with("redis://cache:6379/2", decode_responses=True)
        manager.set_history("s", "refiner", [])
        self.assertEqual(fake_client.expiry["my:prefix:s:refiner"], 1800)

    @patch.dict("os.environ", {"SESSION_MANAGER_BACKEND": "memory"}, clear=False)
    def test_build_memory_manager_from_env(self):
        manager = build_session_manager_from_env()
        self.assertIsInstance(manager, InMemorySessionManager)

    @patch.dict("os.environ", {"SESSION_MANAGER_BACKEND": "bogus"}, clear=False)
    def test_invalid_backend_falls_back_to_memory(self):
        manager = build_session_manager_from_env()
        self.assertIsInstance(manager, InMemorySessionManager)

    @patch.object(sm_module.Redis, "from_url")
    @patch.dict("os.environ", {
        "SESSION_MANAGER_BACKEND": "redis",
        "SESSION_TTL_SECONDS": "not-an-int",
    }, clear=False)
    def test_invalid_ttl_falls_back_to_default(self, mock_from_url):
        fake_client = FakeRedis()
        mock_from_url.return_value = fake_client
        manager = build_session_manager_from_env()

        self.assertIsInstance(manager, RedisSessionManager)
        manager.set_history("s-default-ttl", "refiner", [])
        self.assertEqual(fake_client.expiry["nl2sql:session:s-default-ttl:refiner"], 3600)

    @patch.object(sm_module.Redis, "from_url")
    @patch.dict("os.environ", {
        "SESSION_MANAGER_BACKEND": "redis",
        "SESSION_TTL_POLICY": "sliding",
    }, clear=False)
    def test_sliding_ttl_policy_from_env(self, mock_from_url):
        fake_client = FakeRedis()
        mock_from_url.return_value = fake_client
        manager = build_session_manager_from_env()

        self.assertIsInstance(manager, RedisSessionManager)
        manager.set_history("s-sliding", "refiner", [{"role": "user", "content": "q"}])
        key = "nl2sql:session:s-sliding:refiner"
        fake_client.expiry[key] = 10
        manager.get_history("s-sliding", "refiner")
        self.assertEqual(fake_client.expiry[key], 3600)


if __name__ == "__main__":
    unittest.main()

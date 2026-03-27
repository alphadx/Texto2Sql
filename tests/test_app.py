"""Unit tests for the Texto2Sql service.

All external I/O (OpenAI API, database connections) is mocked so the tests
run without any live services.
"""

import os
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


if __name__ == "__main__":
    unittest.main()

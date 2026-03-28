import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_REQUIRED", "false")
os.environ.setdefault("AUTH_JWT_SECRET", "test-super-secret-key-for-jwt-signing-32chars")
os.environ.setdefault("AUTH_JWT_ALGORITHM", "HS256")

from app.api import create_app
from app.llm.providers import LLMProviderError


_VALID_PAYLOAD = {
    "host": "localhost",
    "usuario": "user",
    "contraseña": "secret",
    "puerto": 5432,
    "nombre_bd": "testdb",
    "motor_bd": "postgres",
    "consulta_nl": "Show all users",
}


class TestApiLLMProviderErrors(unittest.TestCase):
    def setUp(self):
        os.environ["AUTH_REQUIRED"] = "false"
        self.client = TestClient(create_app())

    @patch("app.api.create_engine")
    @patch("app.api.get_schema")
    @patch("app.api.refine_query")
    def test_provider_error_is_mapped_to_http_detail(self, mock_refine, mock_schema, _mock_engine):
        mock_schema.return_value = "TABLE users(id int)"
        mock_refine.side_effect = LLMProviderError(
            provider="gemini",
            message="quota exceeded",
            retryable=False,
            status_code=429,
        )

        response = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD)

        self.assertEqual(response.status_code, 429)
        body = response.json()
        self.assertEqual(body["detail"]["provider"], "gemini")
        self.assertEqual(body["detail"]["retryable"], False)
        self.assertIn("LLM provider error (gemini)", body["detail"]["error"])

    @patch("app.api.create_engine")
    @patch("app.api.get_schema")
    @patch("app.api.refine_query")
    def test_circuit_open_error_returns_provider_and_retryable(self, mock_refine, mock_schema, _mock_engine):
        mock_schema.return_value = "TABLE users(id int)"
        mock_refine.side_effect = LLMProviderError(
            provider="anthropic",
            message="Circuit breaker is open for provider",
            retryable=True,
            status_code=503,
        )

        response = self.client.post("/nl2sql/query", json=_VALID_PAYLOAD)

        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body["detail"]["provider"], "anthropic")
        self.assertEqual(body["detail"]["retryable"], True)
        self.assertIn("LLM provider error (anthropic)", body["detail"]["error"])


if __name__ == "__main__":
    unittest.main()

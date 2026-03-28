import os
import unittest
from unittest.mock import patch

os.environ.setdefault("AUTH_REQUIRED", "true")
os.environ.setdefault("AUTH_JWT_SECRET", "test-super-secret-key-for-jwt-signing-32chars")
os.environ.setdefault("AUTH_JWT_ALGORITHM", "HS256")

from app.llm.converter import generate_sql, refine_query
from app.llm.providers import LLMCompletionResult
from app.llm.session_manager import InMemorySessionManager


class _FakeGateway:
    def __init__(self, text: str):
        self._text = text

    def complete(self, config, messages):
        return LLMCompletionResult(
            text=self._text,
            provider=config.provider,
            model=config.model,
            gateway="fake",
            attempts=1,
            latency_ms=1.0,
        )


class TestConverterGatewayIntegration(unittest.TestCase):
    def setUp(self):
        self.session_manager = InMemorySessionManager()

    @patch("app.llm.converter.get_gateway")
    @patch("app.llm.converter.resolve_runtime_config")
    def test_refine_query_uses_gateway_contract(self, mock_resolve, mock_get_gateway):
        mock_resolve.return_value = type(
            "Cfg", (), {"provider": "openai", "api_key": "k", "model": "gpt-4", "base_url": None}
        )()
        mock_get_gateway.return_value = _FakeGateway("formal description")

        refined = refine_query(
            session_id="s1",
            natural_query="Muéstrame usuarios",
            schema="TABLE users(id int, name text)",
            session_manager=self.session_manager,
            llm_options={"provider": "openai"},
        )

        self.assertEqual(refined, "formal description")

    @patch("app.llm.converter.get_gateway")
    @patch("app.llm.converter.resolve_runtime_config")
    def test_generate_sql_cleans_markdown_and_returns_text(self, mock_resolve, mock_get_gateway):
        mock_resolve.return_value = type(
            "Cfg", (), {"provider": "openai", "api_key": "k", "model": "gpt-4", "base_url": None}
        )()
        mock_get_gateway.return_value = _FakeGateway("```sql\nSELECT 1\n```")

        sql = generate_sql(
            session_id="s2",
            refined_query="Trae una fila",
            schema="TABLE users(id int)",
            db_model="postgres",
            session_manager=self.session_manager,
            llm_options={"provider": "openai"},
        )

        self.assertEqual(sql, "SELECT 1")


if __name__ == "__main__":
    unittest.main()

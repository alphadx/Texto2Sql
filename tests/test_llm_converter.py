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
        self.last_config = None

    def complete(self, config, messages):
        self.last_config = config
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

    @patch("app.llm.converter.get_gateway")
    def test_refine_query_huggingface_serverless_default_wiring(self, mock_get_gateway):
        fake_gateway = _FakeGateway("ok")
        mock_get_gateway.return_value = fake_gateway
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "huggingface",
                "HUGGINGFACE_API_KEY": "hf-key",
            },
            clear=True,
        ):
            refined = refine_query(
                session_id="s3",
                natural_query="Usuarios activos",
                schema="TABLE users(id int)",
                session_manager=self.session_manager,
                llm_options={"provider": "huggingface"},
            )
        self.assertEqual(refined, "ok")
        self.assertEqual(fake_gateway.last_config.provider, "huggingface")
        self.assertEqual(fake_gateway.last_config.model, "Qwen/Qwen2.5-3B-Instruct")
        self.assertEqual(fake_gateway.last_config.base_url, "https://router.huggingface.co/v1")

    @patch("app.llm.converter.get_gateway")
    def test_refine_query_huggingface_dedicated_endpoint_wiring(self, mock_get_gateway):
        fake_gateway = _FakeGateway("ok")
        mock_get_gateway.return_value = fake_gateway
        with patch.dict(os.environ, {"HUGGINGFACE_API_KEY": "hf-key"}, clear=True):
            refined = refine_query(
                session_id="s4",
                natural_query="Usuarios activos",
                schema="TABLE users(id int)",
                session_manager=self.session_manager,
                llm_options={
                    "provider": "huggingface",
                    "base_url": "https://dedicated.hf.endpoint/v1",
                    "model": "Qwen/Qwen2.5-3B-Instruct",
                },
            )
        self.assertEqual(refined, "ok")
        self.assertEqual(fake_gateway.last_config.provider, "huggingface")
        self.assertEqual(fake_gateway.last_config.base_url, "https://dedicated.hf.endpoint/v1")

    @patch("app.llm.converter.get_gateway")
    def test_refine_query_gemini_default_wiring(self, mock_get_gateway):
        fake_gateway = _FakeGateway("ok")
        mock_get_gateway.return_value = fake_gateway
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "gemini",
                "GEMINI_API_KEY": "g-key",
            },
            clear=True,
        ):
            refined = refine_query(
                session_id="s5",
                natural_query="Usuarios activos",
                schema="TABLE users(id int)",
                session_manager=self.session_manager,
                llm_options={"provider": "gemini"},
            )
        self.assertEqual(refined, "ok")
        self.assertEqual(fake_gateway.last_config.provider, "gemini")
        self.assertEqual(fake_gateway.last_config.model, "gemini-2.0-flash-lite")
        self.assertIsNone(fake_gateway.last_config.base_url)

    @patch("app.llm.converter.get_gateway")
    def test_refine_query_mistral_default_wiring(self, mock_get_gateway):
        fake_gateway = _FakeGateway("ok")
        mock_get_gateway.return_value = fake_gateway
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "mistral",
                "MISTRAL_API_KEY": "m-key",
            },
            clear=True,
        ):
            refined = refine_query(
                session_id="s6",
                natural_query="Usuarios activos",
                schema="TABLE users(id int)",
                session_manager=self.session_manager,
                llm_options={"provider": "mistral"},
            )
        self.assertEqual(refined, "ok")
        self.assertEqual(fake_gateway.last_config.provider, "mistral")
        self.assertEqual(fake_gateway.last_config.model, "mistral-small-latest")
        self.assertEqual(fake_gateway.last_config.base_url, "https://api.mistral.ai/v1")

    @patch("app.llm.converter.get_gateway")
    def test_refine_query_claude_alias_wiring(self, mock_get_gateway):
        fake_gateway = _FakeGateway("ok")
        mock_get_gateway.return_value = fake_gateway
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "claude",
                "ANTHROPIC_API_KEY": "a-key",
            },
            clear=True,
        ):
            refined = refine_query(
                session_id="s7",
                natural_query="Usuarios activos",
                schema="TABLE users(id int)",
                session_manager=self.session_manager,
                llm_options={"provider": "claude"},
            )
        self.assertEqual(refined, "ok")
        self.assertEqual(fake_gateway.last_config.provider, "anthropic")
        self.assertEqual(fake_gateway.last_config.model, "claude-3-5-haiku-latest")
        self.assertIsNone(fake_gateway.last_config.base_url)

    @patch("app.llm.converter.get_gateway")
    def test_refine_query_llama_default_wiring(self, mock_get_gateway):
        fake_gateway = _FakeGateway("ok")
        mock_get_gateway.return_value = fake_gateway
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "llama",
                "LLAMA_API_KEY": "l-key",
            },
            clear=True,
        ):
            refined = refine_query(
                session_id="s8",
                natural_query="Usuarios activos",
                schema="TABLE users(id int)",
                session_manager=self.session_manager,
                llm_options={"provider": "llama"},
            )
        self.assertEqual(refined, "ok")
        self.assertEqual(fake_gateway.last_config.provider, "llama")
        self.assertEqual(fake_gateway.last_config.model, "meta-llama/Llama-3.1-8B-Instruct")
        self.assertEqual(fake_gateway.last_config.base_url, "https://router.huggingface.co/v1")

    @patch("app.llm.converter.get_gateway")
    def test_refine_query_copilot_default_wiring(self, mock_get_gateway):
        fake_gateway = _FakeGateway("ok")
        mock_get_gateway.return_value = fake_gateway
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "copilot",
                "COPILOT_API_KEY": "c-key",
            },
            clear=True,
        ):
            refined = refine_query(
                session_id="s9",
                natural_query="Usuarios activos",
                schema="TABLE users(id int)",
                session_manager=self.session_manager,
                llm_options={"provider": "copilot"},
            )
        self.assertEqual(refined, "ok")
        self.assertEqual(fake_gateway.last_config.provider, "copilot")
        self.assertEqual(fake_gateway.last_config.model, "gpt-4.1-mini")
        self.assertEqual(fake_gateway.last_config.base_url, "https://models.inference.ai.azure.com")

    @patch("app.llm.converter.get_gateway")
    def test_refine_query_qwen_default_wiring(self, mock_get_gateway):
        fake_gateway = _FakeGateway("ok")
        mock_get_gateway.return_value = fake_gateway
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "qwen",
                "QWEN_API_KEY": "q-key",
            },
            clear=True,
        ):
            refined = refine_query(
                session_id="s10",
                natural_query="Usuarios activos",
                schema="TABLE users(id int)",
                session_manager=self.session_manager,
                llm_options={"provider": "qwen"},
            )
        self.assertEqual(refined, "ok")
        self.assertEqual(fake_gateway.last_config.provider, "qwen")
        self.assertEqual(fake_gateway.last_config.model, "qwen-plus")
        self.assertEqual(fake_gateway.last_config.base_url, "https://dashscope.aliyuncs.com/compatible-mode/v1")

    @patch("app.llm.converter.get_gateway")
    def test_refine_query_xinghuo_default_wiring(self, mock_get_gateway):
        fake_gateway = _FakeGateway("ok")
        mock_get_gateway.return_value = fake_gateway
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "xinghuo",
                "XINGHUO_API_KEY": "x-key",
            },
            clear=True,
        ):
            refined = refine_query(
                session_id="s11",
                natural_query="Usuarios activos",
                schema="TABLE users(id int)",
                session_manager=self.session_manager,
                llm_options={"provider": "xinghuo"},
            )
        self.assertEqual(refined, "ok")
        self.assertEqual(fake_gateway.last_config.provider, "xinghuo")
        self.assertEqual(fake_gateway.last_config.model, "generalv3.5")
        self.assertEqual(fake_gateway.last_config.base_url, "https://spark-api-open.xf-yun.com/v1")

    @patch("app.llm.converter.get_gateway")
    def test_refine_query_doubao_default_wiring(self, mock_get_gateway):
        fake_gateway = _FakeGateway("ok")
        mock_get_gateway.return_value = fake_gateway
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "doubao",
                "DOUBAO_API_KEY": "d-key",
            },
            clear=True,
        ):
            refined = refine_query(
                session_id="s12",
                natural_query="Usuarios activos",
                schema="TABLE users(id int)",
                session_manager=self.session_manager,
                llm_options={"provider": "doubao"},
            )
        self.assertEqual(refined, "ok")
        self.assertEqual(fake_gateway.last_config.provider, "doubao")
        self.assertEqual(fake_gateway.last_config.model, "doubao-pro-32k")
        self.assertEqual(fake_gateway.last_config.base_url, "https://ark.cn-beijing.volces.com/api/v3")

    @patch("app.llm.converter.get_gateway")
    def test_refine_query_zhipu_default_wiring(self, mock_get_gateway):
        fake_gateway = _FakeGateway("ok")
        mock_get_gateway.return_value = fake_gateway
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "zhipu",
                "ZHIPU_API_KEY": "z-key",
            },
            clear=True,
        ):
            refined = refine_query(
                session_id="s13",
                natural_query="Usuarios activos",
                schema="TABLE users(id int)",
                session_manager=self.session_manager,
                llm_options={"provider": "zhipu"},
            )
        self.assertEqual(refined, "ok")
        self.assertEqual(fake_gateway.last_config.provider, "zhipu")
        self.assertEqual(fake_gateway.last_config.model, "glm-4-flash")
        self.assertEqual(fake_gateway.last_config.base_url, "https://open.bigmodel.cn/api/paas/v4")

    @patch("app.llm.converter.get_gateway")
    def test_refine_query_minimax_default_wiring(self, mock_get_gateway):
        fake_gateway = _FakeGateway("ok")
        mock_get_gateway.return_value = fake_gateway
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "minimax",
                "MINIMAX_API_KEY": "m-key",
            },
            clear=True,
        ):
            refined = refine_query(
                session_id="s14",
                natural_query="Usuarios activos",
                schema="TABLE users(id int)",
                session_manager=self.session_manager,
                llm_options={"provider": "minimax"},
            )
        self.assertEqual(refined, "ok")
        self.assertEqual(fake_gateway.last_config.provider, "minimax")
        self.assertEqual(fake_gateway.last_config.model, "MiniMax-Text-01")
        self.assertEqual(fake_gateway.last_config.base_url, "https://api.minimax.chat/v1")

    @patch("app.llm.converter.get_gateway")
    def test_refine_query_pangu_default_wiring(self, mock_get_gateway):
        fake_gateway = _FakeGateway("ok")
        mock_get_gateway.return_value = fake_gateway
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "pangu",
                "PANGU_API_KEY": "p-key",
            },
            clear=True,
        ):
            refined = refine_query(
                session_id="s15",
                natural_query="Usuarios activos",
                schema="TABLE users(id int)",
                session_manager=self.session_manager,
                llm_options={"provider": "pangu"},
            )
        self.assertEqual(refined, "ok")
        self.assertEqual(fake_gateway.last_config.provider, "pangu")
        self.assertEqual(fake_gateway.last_config.model, "pangu-pro")
        self.assertEqual(fake_gateway.last_config.base_url, "https://modelarts.cn-north-4.myhuaweicloud.com/v1")

    @patch("app.llm.converter.get_gateway")
    def test_refine_query_grok_default_wiring(self, mock_get_gateway):
        fake_gateway = _FakeGateway("ok")
        mock_get_gateway.return_value = fake_gateway
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "grok",
                "GROK_API_KEY": "g-key",
            },
            clear=True,
        ):
            refined = refine_query(
                session_id="s16",
                natural_query="Usuarios activos",
                schema="TABLE users(id int)",
                session_manager=self.session_manager,
                llm_options={"provider": "grok"},
            )
        self.assertEqual(refined, "ok")
        self.assertEqual(fake_gateway.last_config.provider, "grok")
        self.assertEqual(fake_gateway.last_config.model, "grok-2-latest")
        self.assertEqual(fake_gateway.last_config.base_url, "https://api.x.ai/v1")


if __name__ == "__main__":
    unittest.main()

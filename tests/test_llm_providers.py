import os
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

os.environ.setdefault("AUTH_REQUIRED", "true")
os.environ.setdefault("AUTH_JWT_SECRET", "test-super-secret-key-for-jwt-signing-32chars")
os.environ.setdefault("AUTH_JWT_ALGORITHM", "HS256")

from app.llm.providers import (
    AnthropicGateway,
    GeminiGateway,
    LLMProviderError,
    OpenAICompatibleGateway,
    get_gateway,
    normalize_provider,
    resolve_runtime_config,
)


class TestProviderNormalization(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(normalize_provider("claude"), "anthropic")
        self.assertEqual(normalize_provider("google"), "gemini")
        self.assertEqual(normalize_provider("hf"), "huggingface")
        self.assertEqual(normalize_provider("spark"), "xinghuo")
        self.assertEqual(normalize_provider("bytedance"), "doubao")
        self.assertEqual(normalize_provider("glm"), "zhipu")
        self.assertEqual(normalize_provider("mini-max"), "minimax")
        self.assertEqual(normalize_provider("huawei"), "pangu")
        self.assertEqual(normalize_provider("xai"), "grok")


class TestRuntimeConfigResolution(unittest.TestCase):
    def test_request_options_take_precedence(self):
        cfg = resolve_runtime_config(
            {
                "provider": "deepseek",
                "api_key": "req-key",
                "model": "deepseek-chat",
                "base_url": "https://api.deepseek.com",
            }
        )
        self.assertEqual(cfg.provider, "deepseek")
        self.assertEqual(cfg.api_key, "req-key")
        self.assertEqual(cfg.model, "deepseek-chat")
        self.assertEqual(cfg.base_url, "https://api.deepseek.com")

    def test_provider_specific_env_is_used(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "mistral",
                "MISTRAL_API_KEY": "m-key",
                "MISTRAL_MODEL": "mistral-large",
                "MISTRAL_BASE_URL": "https://api.mistral.ai/v1",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.provider, "mistral")
            self.assertEqual(cfg.api_key, "m-key")
            self.assertEqual(cfg.model, "mistral-large")
            self.assertEqual(cfg.base_url, "https://api.mistral.ai/v1")

    def test_provider_specific_env_precedes_global(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "deepseek",
                "LLM_API_KEY": "global-key",
                "LLM_MODEL": "global-model",
                "LLM_BASE_URL": "https://global.example/v1",
                "DEEPSEEK_API_KEY": "deepseek-key",
                "DEEPSEEK_MODEL": "deepseek-chat",
                "DEEPSEEK_BASE_URL": "https://api.deepseek.com/v1",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.provider, "deepseek")
            self.assertEqual(cfg.api_key, "deepseek-key")
            self.assertEqual(cfg.model, "deepseek-chat")
            self.assertEqual(cfg.base_url, "https://api.deepseek.com/v1")

    def test_invalid_base_url_raises(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": "k"}, clear=True):
            with self.assertRaises(ValueError):
                resolve_runtime_config({"base_url": "not-a-valid-url"})

    def test_provider_default_model_is_used_when_model_missing(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "k",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.model, "deepseek-chat")

    def test_huggingface_provider_default_model_is_used_when_model_missing(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "huggingface",
                "HUGGINGFACE_API_KEY": "hf-key",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.model, "Qwen/Qwen2.5-3B-Instruct")

    def test_gemini_provider_default_model_is_used_when_model_missing(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "gemini",
                "GEMINI_API_KEY": "g-key",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.model, "gemini-2.0-flash-lite")

    def test_claude_alias_uses_anthropic_default_model(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "claude",
                "ANTHROPIC_API_KEY": "a-key",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.provider, "anthropic")
            self.assertEqual(cfg.model, "claude-3-5-haiku-latest")

    def test_llama_default_model_and_base_url_are_used(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "llama",
                "LLAMA_API_KEY": "l-key",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.model, "meta-llama/Llama-3.1-8B-Instruct")
            self.assertEqual(cfg.base_url, "https://router.huggingface.co/v1")

    def test_copilot_default_model_and_base_url_are_used(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "copilot",
                "COPILOT_API_KEY": "c-key",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.model, "gpt-4.1-mini")
            self.assertEqual(cfg.base_url, "https://models.inference.ai.azure.com")

    def test_qwen_default_model_and_base_url_are_used(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "qwen",
                "QWEN_API_KEY": "q-key",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.model, "qwen-plus")
            self.assertEqual(cfg.base_url, "https://dashscope.aliyuncs.com/compatible-mode/v1")

    def test_kimi_default_model_and_base_url_are_used(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "kimi",
                "KIMI_API_KEY": "k-key",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.model, "kimi-k2")
            self.assertEqual(cfg.base_url, "https://api.moonshot.cn/v1")

    def test_xinghuo_default_model_and_base_url_are_used(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "xinghuo",
                "XINGHUO_API_KEY": "x-key",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.model, "generalv3.5")
            self.assertEqual(cfg.base_url, "https://spark-api-open.xf-yun.com/v1")

    def test_doubao_default_model_and_base_url_are_used(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "doubao",
                "DOUBAO_API_KEY": "d-key",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.model, "doubao-pro-32k")
            self.assertEqual(cfg.base_url, "https://ark.cn-beijing.volces.com/api/v3")

    def test_zhipu_default_model_and_base_url_are_used(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "zhipu",
                "ZHIPU_API_KEY": "z-key",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.model, "glm-4-flash")
            self.assertEqual(cfg.base_url, "https://open.bigmodel.cn/api/paas/v4")

    def test_minimax_default_model_and_base_url_are_used(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "minimax",
                "MINIMAX_API_KEY": "m-key",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.model, "MiniMax-Text-01")
            self.assertEqual(cfg.base_url, "https://api.minimax.chat/v1")

    def test_pangu_default_model_and_base_url_are_used(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "pangu",
                "PANGU_API_KEY": "p-key",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.model, "pangu-pro")
            self.assertEqual(cfg.base_url, "https://modelarts.cn-north-4.myhuaweicloud.com/v1")

    def test_grok_default_model_and_base_url_are_used(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "grok",
                "GROK_API_KEY": "g-key",
            },
            clear=True,
        ):
            cfg = resolve_runtime_config()
            self.assertEqual(cfg.model, "grok-2-latest")
            self.assertEqual(cfg.base_url, "https://api.x.ai/v1")

    def test_missing_api_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                resolve_runtime_config({"provider": "gemini", "model": "gemini-2.0-flash"})

    def test_unsupported_provider_raises(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "x"}, clear=True):
            with self.assertRaises(ValueError):
                resolve_runtime_config({"provider": "unknown-llm"})


class TestGatewayRegistry(unittest.TestCase):
    def test_selects_native_gateways(self):
        self.assertIsInstance(get_gateway("anthropic"), AnthropicGateway)
        self.assertIsInstance(get_gateway("gemini"), GeminiGateway)

    def test_fallbacks_to_openai_compatible_gateway(self):
        self.assertIsInstance(get_gateway("deepseek"), OpenAICompatibleGateway)
        self.assertIsInstance(get_gateway("qwen"), OpenAICompatibleGateway)
        self.assertIsInstance(get_gateway("kimi"), OpenAICompatibleGateway)
        self.assertIsInstance(get_gateway("xinghuo"), OpenAICompatibleGateway)
        self.assertIsInstance(get_gateway("doubao"), OpenAICompatibleGateway)
        self.assertIsInstance(get_gateway("zhipu"), OpenAICompatibleGateway)
        self.assertIsInstance(get_gateway("minimax"), OpenAICompatibleGateway)
        self.assertIsInstance(get_gateway("pangu"), OpenAICompatibleGateway)
        self.assertIsInstance(get_gateway("grok"), OpenAICompatibleGateway)


class TestNativeGatewayErrorHandling(unittest.TestCase):
    @patch("app.llm.providers.request.urlopen")
    def test_anthropic_wraps_http_errors(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError(
            url="https://api.anthropic.com/v1/messages",
            code=500,
            msg="internal",
            hdrs=None,
            fp=None,
        )
        with patch.dict(os.environ, {"LLM_MAX_RETRIES": "0"}, clear=False):
            gateway = AnthropicGateway()
            with self.assertRaises(LLMProviderError):
                gateway.complete(
                    config=type("Cfg", (), {"provider": "anthropic", "api_key": "k", "model": "claude", "base_url": None})(),
                    messages=[{"role": "user", "content": "hola"}],
                )

    @patch("app.llm.providers.time.sleep")
    @patch("app.llm.providers.request.urlopen")
    def test_gemini_retries_transient_http_errors(self, mock_urlopen, _mock_sleep):
        http_error = HTTPError(
            url="https://generativelanguage.googleapis.com",
            code=503,
            msg="unavailable",
            hdrs=None,
            fp=None,
        )
        success_resp = MagicMock()
        success_resp.__enter__.return_value.read.return_value = (
            b'{\"candidates\":[{\"content\":{\"parts\":[{\"text\":\"ok\"}]}}]}'
        )
        success_resp.__exit__.return_value = False
        mock_urlopen.side_effect = [http_error, success_resp]

        with patch.dict(os.environ, {"LLM_MAX_RETRIES": "1"}, clear=False):
            gateway = GeminiGateway()
            result = gateway.complete(
                config=type("Cfg", (), {"provider": "gemini", "api_key": "k", "model": "gemini-2.0-flash", "base_url": None})(),
                messages=[{"role": "user", "content": "hola"}],
            )

        self.assertEqual(result.text, "ok")
        self.assertEqual(result.gateway, "gemini")

    @patch("app.llm.providers.request.urlopen")
    def test_circuit_breaker_opens_after_threshold(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError(
            url="https://api.anthropic.com/v1/messages",
            code=500,
            msg="internal",
            hdrs=None,
            fp=None,
        )
        cfg = type("Cfg", (), {"provider": "anthropic", "api_key": "k", "model": "claude", "base_url": None})()
        with patch.dict(
            os.environ,
            {
                "LLM_MAX_RETRIES": "0",
                "LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD": "1",
                "LLM_CIRCUIT_BREAKER_RESET_SECONDS": "60",
            },
            clear=False,
        ):
            gateway = AnthropicGateway()
            with self.assertRaises(LLMProviderError):
                gateway.complete(config=cfg, messages=[{"role": "user", "content": "hola"}])
            with self.assertRaises(LLMProviderError) as ctx:
                gateway.complete(config=cfg, messages=[{"role": "user", "content": "hola"}])

        self.assertIn("Circuit breaker is open", str(ctx.exception))
        self.assertEqual(mock_urlopen.call_count, 1)


if __name__ == "__main__":
    unittest.main()

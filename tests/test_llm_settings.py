import os
import unittest
from unittest.mock import patch

os.environ.setdefault("AUTH_REQUIRED", "false")
os.environ.setdefault("AUTH_JWT_SECRET", "test-super-secret-key-for-jwt-signing-32chars")
os.environ.setdefault("AUTH_JWT_ALGORITHM", "HS256")

from app.llm.settings import load_llm_startup_settings_from_env, validate_llm_startup_settings


class TestLLMSettings(unittest.TestCase):
    def test_load_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = load_llm_startup_settings_from_env()
        self.assertEqual(settings.provider, "openai")
        self.assertEqual(settings.model, "gpt-4")
        self.assertEqual(settings.max_retries, 2)

    def test_validate_provider(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "not-supported"}, clear=True):
            settings = load_llm_startup_settings_from_env()
            with self.assertRaises(RuntimeError):
                validate_llm_startup_settings(settings)

    def test_startup_validate_requires_api_key(self):
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "gemini", "LLM_STARTUP_VALIDATE": "true", "LLM_API_KEY": ""},
            clear=True,
        ):
            settings = load_llm_startup_settings_from_env()
            with self.assertRaises(RuntimeError):
                validate_llm_startup_settings(settings)

    def test_startup_validate_accepts_provider_specific_key(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "gemini",
                "LLM_STARTUP_VALIDATE": "true",
                "GEMINI_API_KEY": "g-key",
            },
            clear=True,
        ):
            settings = load_llm_startup_settings_from_env()
            validate_llm_startup_settings(settings)

    def test_provider_defaults_are_used(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": "d-key"}, clear=True):
            settings = load_llm_startup_settings_from_env()
        self.assertEqual(settings.model, "deepseek-chat")
        self.assertEqual(settings.api_key, "d-key")

    def test_huggingface_defaults_are_used(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "huggingface", "HUGGINGFACE_API_KEY": "hf-key"}, clear=True):
            settings = load_llm_startup_settings_from_env()
        self.assertEqual(settings.model, "Qwen/Qwen2.5-3B-Instruct")
        self.assertEqual(settings.api_key, "hf-key")

    def test_gemini_defaults_are_used(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "g-key"}, clear=True):
            settings = load_llm_startup_settings_from_env()
        self.assertEqual(settings.model, "gemini-2.0-flash-lite")
        self.assertEqual(settings.api_key, "g-key")

    def test_claude_alias_default_model_is_used(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "claude", "ANTHROPIC_API_KEY": "a-key"}, clear=True):
            settings = load_llm_startup_settings_from_env()
        self.assertEqual(settings.provider, "anthropic")
        self.assertEqual(settings.model, "claude-3-5-haiku-latest")

    def test_provider_api_key_precedes_global(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "deepseek",
                "LLM_API_KEY": "global-key",
                "DEEPSEEK_API_KEY": "deepseek-key",
            },
            clear=True,
        ):
            settings = load_llm_startup_settings_from_env()
        self.assertEqual(settings.api_key, "deepseek-key")

    def test_validate_rejects_invalid_base_url(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "deepseek",
                "DEEPSEEK_API_KEY": "d-key",
                "DEEPSEEK_BASE_URL": "bad-url",
            },
            clear=True,
        ):
            settings = load_llm_startup_settings_from_env()
            with self.assertRaises(RuntimeError):
                validate_llm_startup_settings(settings)

    def test_provider_alias_claude_maps_to_anthropic(self):
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "claude",
                "ANTHROPIC_API_KEY": "a-key",
            },
            clear=True,
        ):
            settings = load_llm_startup_settings_from_env()
        self.assertEqual(settings.provider, "anthropic")
        self.assertEqual(settings.api_key, "a-key")


if __name__ == "__main__":
    unittest.main()

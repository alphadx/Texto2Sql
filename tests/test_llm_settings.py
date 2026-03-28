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


if __name__ == "__main__":
    unittest.main()

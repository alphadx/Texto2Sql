import os
import unittest
from unittest.mock import patch

os.environ.setdefault("AUTH_REQUIRED", "false")
os.environ.setdefault("AUTH_JWT_SECRET", "test-super-secret-key-for-jwt-signing-32chars")
os.environ.setdefault("AUTH_JWT_ALGORITHM", "HS256")

from scripts.llm_provider_smoke import run


class TestLLMSmokeScript(unittest.TestCase):
    def test_dry_run_outputs_provider_info(self):
        with patch.dict(os.environ, {"LLM_API_KEY": "fake"}, clear=False):
            exit_code = run(["--provider", "deepseek", "--model", "deepseek-chat", "--dry-run"])
        self.assertEqual(exit_code, 0)

    def test_invalid_provider_returns_error(self):
        with self.assertRaises(ValueError):
            run(["--provider", "bad-provider", "--dry-run", "--api-key", "x"])


if __name__ == "__main__":
    unittest.main()

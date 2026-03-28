import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import validate_provider_catalog as validator


class TestProviderCatalogValidator(unittest.TestCase):
    def test_validator_succeeds_with_real_catalog(self):
        self.assertEqual(validator.run(), 0)

    def test_validator_fails_on_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs/providers").mkdir(parents=True, exist_ok=True)
            (root / "docs/providers/deepseek.md").write_text("# DeepSeek")
            bad = {
                "providers": [
                    {"id": "deepseek", "company": "a", "mini_model": "m", "env_api_key": "K", "base_url": "u", "doc": "docs/providers/deepseek.md"},
                    {"id": "deepseek", "company": "b", "mini_model": "m", "env_api_key": "K", "base_url": "u", "doc": "docs/providers/deepseek.md"},
                ]
            }
            (root / "docs/providers/catalog.json").write_text(json.dumps(bad))
            fake_script = root / "scripts/x.py"
            fake_script.parent.mkdir(parents=True, exist_ok=True)
            fake_script.write_text("")

            with patch.object(validator, "__file__", str(fake_script)):
                self.assertEqual(validator.run(), 5)


if __name__ == "__main__":
    unittest.main()

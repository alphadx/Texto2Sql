import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import validate_provider_docs as validator


class TestProviderDocsValidator(unittest.TestCase):
    def test_validator_passes_with_matching_doc(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs/providers").mkdir(parents=True, exist_ok=True)
            catalog = {
                "providers": [
                    {
                        "id": "x",
                        "company": "Provider X",
                        "mini_model": "x-mini",
                        "env_api_key": "X_API_KEY",
                        "base_url": "https://example.test/v1",
                        "doc": "docs/providers/x.md",
                    }
                ]
            }
            (root / "docs/providers/catalog.json").write_text(json.dumps(catalog))
            (root / "docs/providers/x.md").write_text(
                "LLM_PROVIDER=x\nx-mini\nX_API_KEY\nhttps://example.test/v1"
            )
            fake_script = root / "scripts/val.py"
            fake_script.parent.mkdir(parents=True, exist_ok=True)
            fake_script.write_text("")

            with patch.object(validator, "__file__", str(fake_script)):
                self.assertEqual(validator.run(), 0)


if __name__ == "__main__":
    unittest.main()

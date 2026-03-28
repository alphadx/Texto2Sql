import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import validate_typed_snippets as validator


class TestTypedSnippetValidator(unittest.TestCase):
    def test_validator_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs/providers/sdk/x").mkdir(parents=True, exist_ok=True)
            (root / "docs/providers/catalog.json").write_text(json.dumps({
                "providers": [{
                    "id": "x",
                    "company": "X",
                    "mini_model": "x-mini",
                    "env_api_key": "X_API_KEY",
                    "base_url": "https://x.test/v1",
                    "doc": "docs/providers/x.md"
                }]
            }))
            for fname in ["snippet.py", "snippet.mjs", "snippet.php", "snippet.cpp", "snippet.cs", "snippet.java"]:
                (root / "docs/providers/sdk/x" / fname).write_text("x-mini")
            fake = root / "scripts/val.py"
            fake.parent.mkdir(parents=True, exist_ok=True)
            fake.write_text("")

            with patch.object(validator, "__file__", str(fake)):
                self.assertEqual(validator.run(), 0)


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate_typed_snippets as generator


class TestTypedSnippetGenerator(unittest.TestCase):
    def test_generator_creates_provider_snippets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs/providers").mkdir(parents=True, exist_ok=True)
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
            fake = root / "scripts/gen.py"
            fake.parent.mkdir(parents=True, exist_ok=True)
            fake.write_text("")

            with patch.object(generator, "__file__", str(fake)):
                self.assertEqual(generator.run(), 0)

            self.assertTrue((root / "docs/providers/sdk/x/snippet.py").exists())
            self.assertTrue((root / "docs/providers/sdk/README.md").exists())


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate_provider_markdowns as generator


class TestProviderMarkdownGenerator(unittest.TestCase):
    def test_generator_writes_provider_doc(self):
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
            fake_script = root / "scripts/gen.py"
            fake_script.parent.mkdir(parents=True, exist_ok=True)
            fake_script.write_text("")

            with patch.object(generator, "__file__", str(fake_script)):
                code = generator.run()

            self.assertEqual(code, 0)
            out = (root / "docs/providers/x.md").read_text()
            self.assertIn("Provider X", out)
            self.assertIn("X_API_KEY", out)


if __name__ == "__main__":
    unittest.main()

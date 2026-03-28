import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate_provider_artifacts as generator


class TestProviderArtifactGenerator(unittest.TestCase):
    def test_generator_creates_expected_files(self):
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
            matrix = (root / "docs/providers/compatibility-matrix.md").read_text()
            self.assertIn("Provider X", matrix)
            snippets = (root / "docs/providers/snippets-index.md").read_text()
            self.assertIn("x-mini", snippets)


if __name__ == "__main__":
    unittest.main()

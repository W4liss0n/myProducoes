from __future__ import annotations

import importlib
import sys
import unittest


class TestInfrastructureImports(unittest.TestCase):
    def test_settings_repository_import_has_no_pdf_side_effects(self) -> None:
        for module_name in list(sys.modules):
            if module_name.startswith("src.infrastructure") or module_name.startswith("src.core.pdf"):
                sys.modules.pop(module_name, None)

        module = importlib.import_module("src.infrastructure.settings.file_settings_repository")

        self.assertTrue(hasattr(module, "FileSettingsRepository"))
        self.assertNotIn("src.infrastructure.filesystem.gateways", sys.modules)
        self.assertNotIn("src.core.pdf_generator", sys.modules)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.domain.models import PixSettings
from src.infrastructure.settings.file_settings_repository import FileSettingsRepository


class TestFileSettingsRepository(unittest.TestCase):
    def test_roundtrip_pix_and_visible_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pix_file = tmp_path / "config_pix.json"
            columns_file = tmp_path / "columns_config.json"

            with patch("src.infrastructure.settings.file_settings_repository.CONFIG_PIX_FILE", pix_file), patch(
                "src.infrastructure.settings.file_settings_repository.COLUMNS_CONFIG_FILE",
                columns_file,
            ):
                repo = FileSettingsRepository()
                repo.save_pix_settings(
                    PixSettings(
                        nome_beneficiario="Empresa",
                        chave_pix="12345678-1234-1234-1234-123456789012",
                        cidade="São Paulo",
                    )
                )
                repo.save_visible_columns(["Cliente", "Nome"])

                pix = repo.load_pix_settings()
                columns = repo.load_visible_columns()

                self.assertEqual(pix.nome_beneficiario, "Empresa")
                self.assertEqual(pix.cidade, "São Paulo")
                self.assertEqual(columns, ["Cliente", "Nome"])


if __name__ == "__main__":
    unittest.main()

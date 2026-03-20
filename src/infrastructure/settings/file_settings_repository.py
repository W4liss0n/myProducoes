from __future__ import annotations

import json
from collections.abc import Mapping

from ...config.constants import COLUMNS_CONFIG_FILE, CONFIG_PIX_FILE
from ...domain.models import PixSettings


class FileSettingsRepository:
    def load_pix_settings(self) -> PixSettings:
        data = self._load_json(CONFIG_PIX_FILE)
        return PixSettings(
            nome_beneficiario=str(data.get("nome_beneficiario", "")),
            chave_pix=str(data.get("chave_pix", "")),
            cidade=str(data.get("cidade", "")),
        )

    def save_pix_settings(self, settings: PixSettings) -> None:
        self._save_json(CONFIG_PIX_FILE, settings.to_dict())

    def load_visible_columns(self) -> list[str] | None:
        data = self._load_json(COLUMNS_CONFIG_FILE)
        columns = data.get("visible_columns")
        if not isinstance(columns, list):
            return None
        return [str(column) for column in columns]

    def save_visible_columns(self, columns: list[str]) -> None:
        self._save_json(COLUMNS_CONFIG_FILE, {"visible_columns": columns})

    @staticmethod
    def _load_json(path) -> dict[str, object]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    @staticmethod
    def _save_json(path, payload: Mapping[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")

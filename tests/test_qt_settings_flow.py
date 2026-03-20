from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.presentation.qt.dialogs.column_visibility import ColumnVisibilityDialog
from src.presentation.qt.dialogs.manage_types import ManageTypesDialog
from src.presentation.qt.dialogs.pix_config import PixConfigDialog


class TestQtSettingsFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_column_visibility_dialog_requires_one_selection(self) -> None:
        saved: list[list[str]] = []
        dialog = ColumnVisibilityDialog(
            None,
            all_columns=["Cliente", "Nome"],
            visible_columns=["Cliente"],
            on_save=lambda columns: saved.append(columns),
        )

        for checkbox in dialog.checkboxes.values():
            checkbox.setChecked(False)

        with patch("src.presentation.qt.dialogs.column_visibility.QMessageBox.warning") as warning:
            dialog._save()
            warning.assert_called_once()
        self.assertEqual(saved, [])

        dialog.checkboxes["Nome"].setChecked(True)
        dialog._save()
        self.assertEqual(saved, [["Nome"]])

    def test_manage_types_dialog_adds_and_removes_types(self) -> None:
        added: list[str] = []
        removed: list[str] = []
        dialog = ManageTypesDialog(
            None,
            tipos_producao=["Formatura", "Casamento"],
            on_add=lambda nome: added.append(nome) or True,
            on_remove=lambda nome: removed.append(nome) or True,
        )

        dialog.entry.setText("Newborn")
        dialog._add_tipo()
        self.assertIn("Newborn", dialog.get_tipos())
        self.assertEqual(added, ["Newborn"])

        item = dialog.list_widget.findItems("Casamento", Qt.MatchFlag.MatchExactly)[0]
        dialog.list_widget.setCurrentItem(item)
        with patch(
            "src.presentation.qt.dialogs.manage_types.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            dialog._remove_tipo()
        self.assertNotIn("Casamento", dialog.get_tipos())
        self.assertEqual(removed, ["Casamento"])

    def test_pix_config_dialog_saves_valid_data(self) -> None:
        saved: list[dict[str, str]] = []
        dialog = PixConfigDialog(None, on_save=lambda config: saved.append(config))
        dialog.entries["nome_beneficiario"].setText("Empresa")
        dialog.entries["chave_pix"].setText("12345678-1234-1234-1234-123456789012")
        dialog.entries["cidade"].setText("Sao Paulo")

        with patch("src.presentation.qt.dialogs.pix_config.QMessageBox.information") as info:
            dialog._save_config()
            info.assert_called_once()

        self.assertEqual(saved[0]["nome_beneficiario"], "Empresa")
        self.assertEqual(saved[0]["cidade"], "Sao Paulo")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QCursor, QDesktopServices
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from ...config.constants import DATA_DIR
from ...domain.models import PixSettings
from ...presentation.qt.dialogs import (
    ClientsDialog,
    FinancialSummaryDialog,
    ProductionFormDialog,
    RelatorioAbertoDialog,
)
from ...presentation.qt.mappers import ProductionPresentationMapper
from ...presentation.qt.types import ProductionFormData


class DesktopCoordinator:
    def __init__(
        self,
        *,
        main_view_model,
        form_view_model,
        financial_view_model,
        clients_view_model,
        open_report_view_model,
        settings_view_model,
    ) -> None:
        self.main_view_model = main_view_model
        self.form_view_model = form_view_model
        self.financial_view_model = financial_view_model
        self.clients_view_model = clients_view_model
        self.open_report_view_model = open_report_view_model
        self.settings_view_model = settings_view_model

    def open_add_production(self, parent, tipos_producao: list[str], clientes_list: list[str]) -> bool:
        changed = False

        def handle_save(form_data: ProductionFormData):
            nonlocal changed
            payload = ProductionPresentationMapper.form_to_payload(form_data)
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            try:
                result = self.main_view_model.create(payload)
            finally:
                QApplication.restoreOverrideCursor()
            if not result.success:
                QMessageBox.critical(parent, "Erro", result.message)
                return
            QMessageBox.information(parent, "Sucesso", f"Produção adicionada com ID: {result.data.id}")
            changed = True

        dialog = ProductionFormDialog(
            view_model=self.form_view_model,
            parent=parent,
            mode="add",
            tipos_producao=tipos_producao,
            clientes_list=clientes_list,
            on_save=handle_save,
        )
        dialog.exec()
        return changed

    def open_edit_production(
        self,
        parent,
        production_id: int,
        tipos_producao: list[str],
        clientes_list: list[str],
    ) -> bool:
        producao = self.main_view_model.get_production(production_id)
        if producao is None:
            QMessageBox.warning(parent, "Erro", "Produção não encontrada no banco de dados.")
            return False

        changed = False

        def handle_save(form_data: ProductionFormData):
            nonlocal changed
            payload = ProductionPresentationMapper.form_to_payload(form_data)
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            try:
                result = self.main_view_model.update(production_id, payload)
            finally:
                QApplication.restoreOverrideCursor()
            if not result.success:
                QMessageBox.critical(parent, "Erro", result.message)
                return
            QMessageBox.information(parent, "Sucesso", "Produção atualizada com sucesso!")
            changed = True

        dialog = ProductionFormDialog(
            view_model=self.form_view_model,
            parent=parent,
            mode="edit",
            initial_data=ProductionPresentationMapper.production_to_form_data(producao),
            tipos_producao=tipos_producao,
            clientes_list=clientes_list,
            on_save=handle_save,
        )
        dialog.exec()
        return changed

    def open_open_report_dialog(self, parent) -> bool:
        dialog = RelatorioAbertoDialog(
            view_model=self.open_report_view_model,
            parent=parent,
            on_generate=lambda cliente, ids: self._generate_open_report(parent, cliente, ids),
        )
        dialog.exec()
        return False

    def _generate_open_report(self, parent, cliente: str, production_ids: list[int]) -> None:
        data_atual = datetime.now().strftime("%Y-%m-%d")
        nome_arquivo = f"Relatorio Aberto - {data_atual} - {cliente}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            parent,
            "Salvar Relatório PDF",
            str(DATA_DIR / nome_arquivo),
            "PDF Files (*.pdf)",
        )
        if not file_path:
            return

        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        try:
            result = self.open_report_view_model.generate_report(
                cliente=cliente,
                output_path=Path(file_path),
                production_ids=production_ids,
            )
        finally:
            QApplication.restoreOverrideCursor()

        if not result.success:
            QMessageBox.warning(parent, "Erro", result.message)
            return

        reply = QMessageBox.question(
            parent,
            "Sucesso",
            "Relatório PDF gerado com sucesso!\n\nDeseja abrir o arquivo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes and result.output_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(result.output_path.resolve())))

    def open_financial_summary(self, parent) -> None:
        dialog = FinancialSummaryDialog(view_model=self.financial_view_model, parent=parent)
        dialog.exec()

    def open_clients_dialog(self, parent) -> bool:
        dialog = ClientsDialog(view_model=self.clients_view_model, parent=parent)
        dialog.exec()
        return dialog.changed

    def load_pix_settings(self) -> PixSettings:
        return self.settings_view_model.load_pix_settings()

    def save_pix_settings(self, config: dict[str, str]) -> None:
        self.settings_view_model.save_pix_settings(
            PixSettings(
                nome_beneficiario=config.get("nome_beneficiario", ""),
                chave_pix=config.get("chave_pix", ""),
                cidade=config.get("cidade", ""),
            )
        )

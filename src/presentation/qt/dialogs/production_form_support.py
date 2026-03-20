from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QComboBox, QDateEdit, QLineEdit, QWidget

from ....domain.models import FolderInspection
from ..types import ProductionFormData
from ..widgets import AutocompleteLineEdit, MoneyLineEdit


@dataclass(slots=True)
class ProductionFormFields:
    cliente: AutocompleteLineEdit
    nome: QLineEdit
    tipo_producao: QComboBox
    data_recebimento: QDateEdit
    data_conclusao: QDateEdit
    status: QComboBox
    status_pagamento: QComboBox
    quantidade_alunos: QLineEdit
    quantidade_fotos: QLineEdit
    quantidade_kits: QLineEdit
    quantidade_capas: QLineEdit
    valor_por_foto: MoneyLineEdit
    valor_por_kit: MoneyLineEdit
    valor_por_capa: MoneyLineEdit

    def as_widget_map(self) -> dict[str, QWidget]:
        return {
            "cliente": self.cliente,
            "nome": self.nome,
            "tipo_producao": self.tipo_producao,
            "data_recebimento": self.data_recebimento,
            "data_conclusao": self.data_conclusao,
            "status": self.status,
            "status_pagamento": self.status_pagamento,
            "quantidade_alunos": self.quantidade_alunos,
            "quantidade_fotos": self.quantidade_fotos,
            "quantidade_kits": self.quantidade_kits,
            "quantidade_capas": self.quantidade_capas,
            "valor_por_foto": self.valor_por_foto,
            "valor_por_kit": self.valor_por_kit,
            "valor_por_capa": self.valor_por_capa,
        }


class ProductionFormValidator:
    def populate(self, fields: ProductionFormFields, data: ProductionFormData) -> None:
        fields.cliente.setText(data.cliente)
        fields.nome.setText(data.nome)
        self._set_combo_value(fields.tipo_producao, data.tipo_producao)
        self._set_date_value(fields.data_recebimento, data.data_recebimento)
        self._set_date_value(fields.data_conclusao, data.data_conclusao)
        self._set_combo_value(fields.status, data.status)
        self._set_combo_value(fields.status_pagamento, data.status_pagamento)
        fields.quantidade_alunos.setText(str(data.quantidade_alunos))
        fields.quantidade_fotos.setText(str(data.quantidade_fotos))
        fields.quantidade_kits.setText(str(data.quantidade_kits))
        fields.quantidade_capas.setText(str(data.quantidade_capas))
        fields.valor_por_foto.setValue(float(data.valor_por_foto or 0.0))
        fields.valor_por_kit.setValue(float(data.valor_por_kit or 0.0))
        fields.valor_por_capa.setValue(float(data.valor_por_capa or 0.0))

    def collect(
        self,
        fields: ProductionFormFields,
        *,
        initial_data: ProductionFormData,
        pasta_producao: str,
    ) -> ProductionFormData:
        return ProductionFormData(
            cliente=fields.cliente.text().strip(),
            nome=fields.nome.text().strip(),
            tipo_producao=fields.tipo_producao.currentText().strip(),
            data_recebimento=fields.data_recebimento.date().toString("yyyy-MM-dd"),
            data_conclusao=fields.data_conclusao.date().toString("yyyy-MM-dd"),
            status=fields.status.currentText().strip(),
            status_pagamento=fields.status_pagamento.currentText().strip(),
            quantidade_alunos=self._parse_int(fields.quantidade_alunos.text()),
            quantidade_fotos=self._parse_int(fields.quantidade_fotos.text()),
            quantidade_kits=self._parse_int(fields.quantidade_kits.text()),
            quantidade_capas=self._parse_int(fields.quantidade_capas.text()),
            valor_por_foto=fields.valor_por_foto.value(),
            valor_por_kit=fields.valor_por_kit.value(),
            valor_por_capa=fields.valor_por_capa.value(),
            valor_recebido=initial_data.valor_recebido,
            saldo=initial_data.saldo,
            pasta_producao=pasta_producao,
            codigo=initial_data.codigo,
            relatorio=initial_data.relatorio,
        )

    def validate_required(self, data: ProductionFormData) -> str | None:
        if not data.cliente:
            return "O campo Cliente é obrigatório!"
        if not data.nome:
            return "O campo Nome é obrigatório!"
        if not data.tipo_producao:
            return "O campo Tipo de Serviço é obrigatório!"
        return None

    def calculate_total(self, fields: ProductionFormFields) -> float:
        total = 0.0
        total += self._parse_int(fields.quantidade_fotos.text()) * fields.valor_por_foto.value()
        total += self._parse_int(fields.quantidade_kits.text()) * fields.valor_por_kit.value()
        total += self._parse_int(fields.quantidade_capas.text()) * fields.valor_por_capa.value()
        return total

    def apply_folder_name(self, fields: ProductionFormFields, folder_name: str) -> None:
        if folder_name:
            fields.nome.setText(folder_name)

    def apply_folder_inspection(self, fields: ProductionFormFields, inspection: FolderInspection) -> None:
        fields.quantidade_fotos.setText(str(inspection.total_fotos))
        fields.quantidade_alunos.setText(str(inspection.total_alunos))
        fields.quantidade_kits.setText(str(inspection.total_kits))

    @staticmethod
    def _parse_int(value: str) -> int:
        normalized = value.strip()
        return int(normalized) if normalized else 0

    @staticmethod
    def _set_combo_value(widget: QComboBox, value: str) -> None:
        if not value:
            return
        index = widget.findText(value)
        if index >= 0:
            widget.setCurrentIndex(index)

    @staticmethod
    def _set_date_value(widget: QDateEdit, value: str | None) -> None:
        if value:
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    date_obj = datetime.strptime(value.split()[0], fmt)
                    widget.setDate(QDate(date_obj.year, date_obj.month, date_obj.day))
                    return
                except ValueError:
                    continue
        widget.setDate(QDate.currentDate())

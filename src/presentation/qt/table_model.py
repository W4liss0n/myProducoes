from __future__ import annotations

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt

from .types import ProductionTableRow


class ProductionTableModel(QAbstractTableModel):
    def __init__(self, columns: list[str], parent=None) -> None:
        super().__init__(parent)
        self._columns = columns
        self._items: list[ProductionTableRow] = []

    def set_items(self, items: list[ProductionTableRow]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._items)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._columns)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal and 0 <= section < len(self._columns):
            return self._columns[section]
        return section + 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if not index.isValid():
            return None

        row = self._items[index.row()]
        column_name = self._columns[index.column()]

        if role == Qt.ItemDataRole.DisplayRole:
            value = row.values.get(column_name, "")
            if isinstance(value, float) and column_name.startswith("Valor"):
                return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return str(value) if value is not None else ""

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignCenter)

        if role == Qt.ItemDataRole.UserRole:
            return row.production_id

        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:  # noqa: N802
        if not 0 <= column < len(self._columns):
            return

        column_name = self._columns[column]
        reverse = order == Qt.SortOrder.DescendingOrder
        self.layoutAboutToBeChanged.emit()
        self._items.sort(
            key=lambda item: item.values.get(column_name, ""),
            reverse=reverse,
        )
        self.layoutChanged.emit()

    def row_at(self, row: int) -> ProductionTableRow | None:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def update_item(self, updated: ProductionTableRow) -> None:
        for row, item in enumerate(self._items):
            if item.production_id != updated.production_id:
                continue
            self._items[row] = updated
            top_left = self.index(row, 0)
            bottom_right = self.index(row, len(self._columns) - 1)
            self.dataChanged.emit(top_left, bottom_right)
            return

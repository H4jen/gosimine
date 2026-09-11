from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gosimine.database import Database, Miner


class AddMinerDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add miner")

        self.name_input = QLineEdit()
        self.ticker_input = QLineEdit()
        self.commodity_input = QLineEdit("Gold")
        self.stage_input = QLineEdit("Explorer")

        form = QFormLayout(self)
        form.addRow("Company name", self.name_input)
        form.addRow("Ticker", self.ticker_input)
        form.addRow("Primary commodity", self.commodity_input)
        form.addRow("Stage", self.stage_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        form.addRow(buttons)

    def values(self) -> tuple[str, str, str, str]:
        return (
            self.name_input.text(),
            self.ticker_input.text(),
            self.commodity_input.text(),
            self.stage_input.text(),
        )

    def accept(self) -> None:
        if not self.name_input.text().strip() or not self.ticker_input.text().strip():
            QMessageBox.warning(self, "Missing information", "Company name and ticker are required.")
            return
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database
        self.setWindowTitle("Gosimine")
        self.resize(1100, 680)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Company", "Ticker", "Commodity", "Stage"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self.show_selected_miner)

        self.detail = QLabel("Select a miner to view its research workspace.")
        self.detail.setWordWrap(True)
        self.detail.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.detail.setContentsMargins(24, 24, 24, 24)

        splitter = QSplitter()
        splitter.addWidget(self.table)
        splitter.addWidget(self.detail)
        splitter.setSizes([700, 400])

        add_button = QPushButton("Add miner")
        add_button.clicked.connect(self.add_miner)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.addWidget(add_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(splitter)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        self.refresh_miners()

    def refresh_miners(self) -> None:
        miners = self.database.list_miners()
        self.table.setRowCount(len(miners))
        for row, miner in enumerate(miners):
            for column, value in enumerate(
                [miner.name, miner.ticker, miner.primary_commodity, miner.stage]
            ):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, miner)
                self.table.setItem(row, column, item)

    def show_selected_miner(self) -> None:
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
        miner = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if isinstance(miner, Miner):
            self.detail.setText(
                f"{miner.name}\n\n"
                f"Ticker: {miner.ticker}\n"
                f"Primary commodity: {miner.primary_commodity}\n"
                f"Stage: {miner.stage}\n\n"
                "Research history and source tracking will appear here."
            )

    def add_miner(self) -> None:
        dialog = AddMinerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.add_miner(*dialog.values())
            self.refresh_miners()


def main() -> None:
    application = QApplication(sys.argv)
    database = Database(Path("data") / "gosimine.sqlite3")
    window = MainWindow(database)
    window.show()
    exit_code = application.exec()
    database.close()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()

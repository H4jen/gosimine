from __future__ import annotations

import re
import sys
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QDateEdit,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gosimine.database import Database, Miner
from gosimine.market_data import refresh_market_data
from gosimine.seed import initialize_database
from gosimine.analysis import AnalysisInputs, calculate_analysis
from gosimine.settings import APPLICATION_SETTINGS, BASE_CURRENCY


PARAMETER_UNITS = {
    "annual_production_ounces": "AgEq oz/year",
    "total_resource_equivalent_ounces": "AgEq oz",
    "aisc_per_ounce": "USD/AgEq oz",
    "mine_life_years": "years",
    "after_tax_npv_usd": "USD",
    "cash_usd": "USD",
    "total_debt_usd": "USD",
    "potential_conversion_shares": "shares",
    "basic_shares_outstanding": "shares",
    "study_discount_rate_percent": "%",
}

METRIC_EXPLANATIONS = {
    "Share price": "Latest market price for this listing. Source: the latest stored market snapshot.",
    "Risked NAV / share": "NAV per basic share multiplied by the investor-entered development risk factor.",
    "Risked NAV / SP": "Risked NAV per basic share divided by the current share price. Above 1.0x means the risked screening value exceeds the share price.",
    "NAV / share": "After-tax project NPV plus cash minus total debt, divided by basic shares outstanding.",
    "NAV / SP": "NAV per basic share divided by the current share price. Above 1.0x means the NAV estimate exceeds the share price.",
    "Annual margin / share": "Annual equivalent-metal production multiplied by current margin per equivalent-metal ounce, divided by basic shares. This is an operating proxy, not EPS.",
    "Lifetime margin / SP": "Undiscounted lifetime operating-margin proxy per share divided by current share price. It is not project NPV or earnings.",
    "AISC": "Reported all-in sustaining cost per equivalent-metal ounce. It is the cost input subtracted from the equivalent-metal price to calculate the margin proxy.",
    "AgEq price": "Payable silver and gold volumes valued at the latest stored metal prices, expressed per equivalent-metal ounce.",
    "Margin per AgEq oz": "AgEq price minus reported AISC. It is a screening margin, not reported net income.",
    "Annual AgEq oz / share": "Annual equivalent-metal production divided by basic shares outstanding.",
    "Lifetime AgEq oz / share": "Annual equivalent-metal production multiplied by mine life, divided by basic shares outstanding.",
    "Lifetime margin / share": "Annual operating-margin proxy per share multiplied by mine life. It is undiscounted.",
    "Resource AgEq oz / share": "Total measured, indicated, and inferred equivalent-metal resources divided by basic shares. These are in-situ resource ounces, not a mine plan or reserves.",
    "Resource margin / SP": "Total resource equivalent-metal ounces per share multiplied by the current margin per equivalent-metal ounce, divided by share price. It is a speculative resource screening ratio, not NPV or expected profit.",
    "After-tax NPV / share": "Company-reported after-tax feasibility-study NPV divided by basic shares. Review its source and study metal-price assumptions in Model inputs.",
    "NPV / SP": "After-tax study NPV per basic share divided by the current share price. Above 1.0x means the study NPV estimate exceeds the share price.",
    "Future AgEq price": "Scenario payable-metal prices expressed per equivalent-metal ounce. This is a personal scenario, not a sourced market fact.",
    "Future annual margin / share": "Scenario annual operating-margin proxy per basic share.",
    "Future lifetime margin / share": "Scenario undiscounted lifetime operating-margin proxy per basic share.",
    "Future lifetime margin / SP": "Scenario lifetime operating-margin proxy per share divided by current share price.",
    "Future resource margin / SP": "Scenario total resource equivalent-metal ounces per share multiplied by scenario margin per equivalent-metal ounce, divided by share price. It is a speculative resource screening ratio, not NPV or expected profit.",
}

LIFECYCLE_STATUSES = (
    "Explorer",
    "Developer / permitting",
    "Construction",
    "Commissioning / ramp-up",
    "Producer",
    "Expansion",
    "Care and maintenance",
    "Suspended / distressed",
    "Closed / reclaimed",
)

APPLICATION_STYLE = """
QMainWindow { background: #d7e0d9; color: #1c2822; }
QWidget#workspace { background: #d7e0d9; }
QDialog { background: #ffffff; border: 2px solid #216b4d; color: #1c2822; }
QWidget { font-family: "Noto Sans", "DejaVu Sans", sans-serif; font-size: 13px; }
QTableWidget, QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit, QTextEdit {
    background: #ffffff; border: 1px solid #cdd6cf; border-radius: 4px; padding: 5px 7px;
}
QTableWidget::item:selected { background: #dcebe2; color: #1c2822; }
QHeaderView::section {
    background: #e8ece8; border: 0; border-bottom: 1px solid #cdd6cf;
    color: #4e5f55; font-weight: 600; padding: 7px;
}
QPushButton {
    background: #ffffff; border: 1px solid #adbbb1; border-radius: 4px; padding: 6px 10px;
}
QPushButton:hover { background: #eaf1eb; }
QPushButton#primary-action { background: #216b4d; border-color: #216b4d; color: white; font-weight: 600; }
QPushButton#primary-action:hover { background: #18563d; }
QLabel#dashboard-title { color: #183128; font-size: 24px; font-weight: 700; }
QLabel#dashboard-subtitle { color: #5a6b61; }
QLabel#section-heading {
    border-top: 1px solid #d4ddd6; color: #216b4d; font-size: 15px; font-weight: 700;
    margin-top: 12px; padding-top: 12px;
}
QLabel#status-value {
    background: #e2eee6; border: 1px solid #c4d7ca; border-radius: 4px;
    color: #1f583f; font-weight: 600; padding: 8px;
}
QLabel#metric-label { color: #5a6b61; font-size: 11px; }
QLabel#metric-value { color: #183128; font-size: 20px; font-weight: 700; }
QLabel#metric-marker { color: #5a6b61; font-size: 11px; font-weight: 400; }
QLabel#analysis-note { color: #5a6b61; font-size: 10px; }
QTabWidget::pane { border: 1px solid #cdd6cf; background: white; }
QTabBar::tab { padding: 7px 12px; }
"""


def is_supported_parameter(parameter: str) -> bool:
    return (
        parameter in PARAMETER_UNITS
        or bool(re.fullmatch(r"annual_payable_[a-z]+_ounces", parameter))
        or bool(re.fullmatch(r"study_metal_price_[a-z]+_usd_per_ounce", parameter))
    )


def metric_explanation(label: str) -> str:
    metric_name = label.split(" (", 1)[0]
    return METRIC_EXPLANATIONS.get(metric_name, "Derived from the current stored model inputs.")


def configure_dialog(dialog: QDialog) -> None:
    palette = dialog.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#1c2822"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#1c2822"))
    dialog.setPalette(palette)
    dialog.setAutoFillBackground(True)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)


class AddMinerDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        configure_dialog(self)
        self.setWindowTitle("Add miner")

        self.name_input = QLineEdit()
        self.ticker_input = QLineEdit()
        self.commodity_input = QLineEdit("Gold")
        self.stage_input = QLineEdit("Explorer")
        self.trading_currency_input = QLineEdit("USD")

        form = QFormLayout(self)
        form.addRow("Company name", self.name_input)
        form.addRow("Ticker", self.ticker_input)
        form.addRow("Primary commodity", self.commodity_input)
        form.addRow("Stage", self.stage_input)
        form.addRow("Trading currency", self.trading_currency_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        form.addRow(buttons)
        form.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

    def values(self) -> tuple[str, str, str, str, str]:
        return (
            self.name_input.text(),
            self.ticker_input.text(),
            self.commodity_input.text(),
            self.stage_input.text(),
            self.trading_currency_input.text(),
        )

    def accept(self) -> None:
        if not self.name_input.text().strip() or not self.ticker_input.text().strip():
            QMessageBox.warning(self, "Missing information", "Company name and ticker are required.")
            return
        super().accept()


class CatalogDialog(QDialog):
    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        configure_dialog(self)
        self.database = database
        self.selected_ticker: str | None = None
        self.setWindowTitle("Select miner from catalog")
        self.resize(680, 420)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search company, ticker, or commodity")
        self.search_input.textChanged.connect(self.refresh_catalog)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Company", "Ticker", "Commodity", "Stage"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemDoubleClicked.connect(lambda _: self.accept())

        layout = QVBoxLayout(self)
        layout.addWidget(self.search_input)
        layout.addWidget(self.table)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Open
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.refresh_catalog()

    def refresh_catalog(self) -> None:
        records = self.database.list_catalog_miners(self.search_input.text())
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            for column, value in enumerate(
                [record.name, record.ticker, record.primary_commodity, record.stage]
            ):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, record.ticker)
                self.table.setItem(row, column, item)

    def accept(self) -> None:
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No miner selected", "Select a catalog listing.")
            return
        self.selected_ticker = selected_items[0].data(Qt.ItemDataRole.UserRole)
        super().accept()


class HistoryDialog(QDialog):
    def __init__(self, database: Database, miner: Miner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        configure_dialog(self)
        self.setWindowTitle(f"History: {miner.ticker}")
        self.resize(860, 520)
        tabs = QTabWidget()
        tabs.addTab(
            self._table(
                ["Date", "Parameter", "Value", "Unit", "Source"],
                [
                    [entry.as_of_date, entry.parameter, f"{entry.value:,.12g}", entry.unit, entry.source]
                    for entry in database.list_parameter_history(miner.id)
                ],
            ),
            "Model inputs",
        )
        tabs.addTab(
            self._table(
                ["Date", "Status", "Source"],
                [
                    [entry.as_of_date, entry.status, entry.source]
                    for entry in database.list_lifecycle_status_history(miner.id)
                ],
            ),
            "Lifecycle",
        )
        tabs.addTab(
            self._table(
                ["Target/outcome", "Category", "Title", "Status", "Detail", "Source"],
                [
                    [
                        entry.target_date,
                        entry.category,
                        entry.title,
                        entry.status,
                        entry.detail,
                        entry.source,
                    ]
                    for entry in database.list_milestones(miner.id)
                ],
            ),
            "Milestones",
        )
        tabs.addTab(
            self._table(
                ["Date", "Note", "Source", "Thesis change", "Catalyst", "Open question"],
                [
                    [
                        entry.entry_date,
                        entry.note,
                        entry.source,
                        entry.thesis_change,
                        entry.catalyst,
                        entry.open_question,
                    ]
                    for entry in database.list_research_entries(miner.id)
                ],
            ),
            "Research",
        )
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        close_button = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button.rejected.connect(self.reject)
        layout.addWidget(close_button)

    @staticmethod
    def _table(headers: list[str], rows: list[list[str]]) -> QTableWidget:
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        for row_number, row in enumerate(rows):
            for column_number, value in enumerate(row):
                table.setItem(row_number, column_number, QTableWidgetItem(value))
        return table


class AddResearchEntryDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        configure_dialog(self)
        self.setWindowTitle("Add research note")

        self.entry_date_input = QDateEdit(QDate.currentDate())
        self.entry_date_input.setCalendarPopup(True)
        self.note_input = QTextEdit()
        self.source_input = QLineEdit()
        self.thesis_change_input = QLineEdit()
        self.catalyst_input = QLineEdit()
        self.open_question_input = QLineEdit()

        form = QFormLayout(self)
        form.addRow("Date", self.entry_date_input)
        form.addRow("Note", self.note_input)
        form.addRow("Source", self.source_input)
        form.addRow("Thesis change", self.thesis_change_input)
        form.addRow("Catalyst", self.catalyst_input)
        form.addRow("Open question", self.open_question_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        form.addRow(buttons)

    def values(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.entry_date_input.date().toString("yyyy-MM-dd"),
            self.note_input.toPlainText(),
            self.source_input.text(),
            self.thesis_change_input.text(),
            self.catalyst_input.text(),
            self.open_question_input.text(),
        )

    def accept(self) -> None:
        if not self.note_input.toPlainText().strip():
            QMessageBox.warning(self, "Missing information", "A research note is required.")
            return
        super().accept()


class AddMilestoneDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        configure_dialog(self)
        self.setWindowTitle("Add milestone")

        self.category_input = QLineEdit()
        self.title_input = QLineEdit()
        self.target_date_input = QLineEdit()
        self.status_input = QLineEdit("Planned")
        self.detail_input = QTextEdit()
        self.source_input = QLineEdit("Manual")

        form = QFormLayout(self)
        form.addRow("Category", self.category_input)
        form.addRow("Title", self.title_input)
        form.addRow("Target date", self.target_date_input)
        form.addRow("Status", self.status_input)
        form.addRow("Detail", self.detail_input)
        form.addRow("Source", self.source_input)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        form.addRow(buttons)

    def values(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.category_input.text(),
            self.title_input.text(),
            self.target_date_input.text(),
            self.status_input.text(),
            self.detail_input.toPlainText(),
            self.source_input.text(),
        )

    def accept(self) -> None:
        required = (
            self.category_input.text(),
            self.title_input.text(),
            self.target_date_input.text(),
            self.status_input.text(),
            self.source_input.text(),
        )
        if not all(value.strip() for value in required):
            QMessageBox.warning(self, "Missing information", "Complete all milestone fields.")
            return
        super().accept()


class UpdateMilestoneDialog(QDialog):
    def __init__(self, category: str, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        configure_dialog(self)
        self.setWindowTitle("Record milestone outcome")
        self.category = category
        self.title = title
        self.outcome_date_input = QDateEdit(QDate.currentDate())
        self.outcome_date_input.setCalendarPopup(True)
        self.status_input = QComboBox()
        self.status_input.addItems(("Completed", "Delayed", "Cancelled", "Updated"))
        self.outcome_input = QTextEdit()
        self.thesis_impact_input = QLineEdit()
        self.source_input = QLineEdit("Manual")

        form = QFormLayout(self)
        form.addRow("Milestone", QLabel(f"{category}: {title}"))
        form.addRow("Outcome date", self.outcome_date_input)
        form.addRow("Status", self.status_input)
        form.addRow("Actual outcome", self.outcome_input)
        form.addRow("Thesis impact", self.thesis_impact_input)
        form.addRow("Source", self.source_input)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        form.addRow(buttons)

    def values(self) -> tuple[str, str, str, str, str, str]:
        detail = (
            f"Actual outcome: {self.outcome_input.toPlainText().strip()}\n"
            f"Thesis impact: {self.thesis_impact_input.text().strip()}"
        )
        return (
            self.category,
            self.title,
            self.outcome_date_input.date().toString("yyyy-MM-dd"),
            self.status_input.currentText(),
            detail,
            self.source_input.text(),
        )

    def accept(self) -> None:
        if not self.outcome_input.toPlainText().strip() or not self.source_input.text().strip():
            QMessageBox.warning(self, "Missing information", "Outcome and source are required.")
            return
        super().accept()


class SaveScenarioDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        configure_dialog(self)
        self.setWindowTitle("Save scenario")
        self.name_input = QLineEdit()
        form = QFormLayout(self)
        form.addRow("Scenario name", self.name_input)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        form.addRow(buttons)

    def value(self) -> str:
        return self.name_input.text()

    def accept(self) -> None:
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Missing information", "A scenario name is required.")
            return
        super().accept()


class AddModelInputDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        configure_dialog(self)
        self.setWindowTitle("Add model input")
        self.parameter_input = QComboBox()
        self.parameter_input.setEditable(True)
        self.parameter_input.addItems(sorted(PARAMETER_UNITS))
        self.value_input = QDoubleSpinBox()
        self.value_input.setRange(0.000000001, 10_000_000_000_000)
        self.value_input.setDecimals(9)
        self.unit_input = QLineEdit()
        self.as_of_date_input = QDateEdit(QDate.currentDate())
        self.as_of_date_input.setCalendarPopup(True)
        self.source_input = QLineEdit("Manual")
        self.parameter_input.currentTextChanged.connect(self._set_suggested_unit)

        form = QFormLayout(self)
        form.addRow("Parameter", self.parameter_input)
        form.addRow("Value", self.value_input)
        form.addRow("Unit", self.unit_input)
        form.addRow("As of date", self.as_of_date_input)
        form.addRow("Source", self.source_input)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        form.addRow(buttons)
        self._set_suggested_unit(self.parameter_input.currentText())

    def _set_suggested_unit(self, parameter: str) -> None:
        if parameter in PARAMETER_UNITS:
            self.unit_input.setText(PARAMETER_UNITS[parameter])

    def values(self) -> tuple[str, float, str, str, str]:
        return (
            self.parameter_input.currentText().strip(),
            self.value_input.value(),
            self.unit_input.text(),
            self.as_of_date_input.date().toString("yyyy-MM-dd"),
            self.source_input.text(),
        )

    def accept(self) -> None:
        parameter, _, unit, _, source = self.values()
        if not is_supported_parameter(parameter):
            QMessageBox.warning(self, "Unsupported parameter", "Choose a supported parameter name.")
            return
        if not unit.strip() or not source.strip():
            QMessageBox.warning(self, "Missing information", "Unit and source are required.")
            return
        super().accept()


class UpdateLifecycleStatusDialog(QDialog):
    def __init__(self, current_status: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        configure_dialog(self)
        self.setWindowTitle("Update lifecycle status")
        self.status_input = QComboBox()
        self.status_input.addItems(LIFECYCLE_STATUSES)
        self.status_input.setCurrentText(current_status)
        self.as_of_date_input = QDateEdit(QDate.currentDate())
        self.as_of_date_input.setCalendarPopup(True)
        self.source_input = QLineEdit("Manual")

        form = QFormLayout(self)
        form.addRow("Status", self.status_input)
        form.addRow("As of date", self.as_of_date_input)
        form.addRow("Source", self.source_input)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        form.addRow(buttons)

    def values(self) -> tuple[str, str, str]:
        return (
            self.status_input.currentText(),
            self.as_of_date_input.date().toString("yyyy-MM-dd"),
            self.source_input.text(),
        )

    def accept(self) -> None:
        if not self.source_input.text().strip():
            QMessageBox.warning(self, "Missing information", "A source is required.")
            return
        super().accept()


class SettingsDialog(QDialog):
    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        configure_dialog(self)
        self.database = database
        self.inputs: dict[str, QComboBox] = {}
        self.setWindowTitle("Settings")

        form = QFormLayout(self)
        for definition in APPLICATION_SETTINGS:
            value = database.get_current_application_setting(definition.key)
            setting_input = QComboBox()
            setting_input.addItems(definition.choices)
            setting_input.setCurrentText(
                value.value if value is not None else definition.default_value
            )
            self.inputs[definition.key] = setting_input
            form.addRow(definition.label, setting_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        form.addRow(buttons)

    def accept(self) -> None:
        for definition in APPLICATION_SETTINGS:
            value = self.inputs[definition.key].currentText()
            current = self.database.get_current_application_setting(definition.key)
            if current is None or current.value != value:
                self.database.set_application_setting(definition.key, value)
        super().accept()


class MinerDashboard(QWidget):
    def __init__(self, database: Database, miner: Miner) -> None:
        super().__init__()
        self.database = database
        self.miner = miner
        self.inputs_visible = False
        self.scenario_prices: dict[str, float] = {}
        self.development_risk_factor = 0.70
        self.additional_dilution_shares = 0.0
        self.active_tab = 0
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(24, 24, 24, 24)
        self.layout = self.root_layout
        self.render()

    def render(self) -> None:
        while self.root_layout.count():
            item = self.root_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        title = QLabel(f"{self.miner.name} ({self.miner.ticker})")
        title.setObjectName("dashboard-title")
        self.root_layout.addWidget(title)
        subtitle = QLabel(
            f"{self.miner.primary_commodity} | {self.miner.trading_currency} listing"
        )
        subtitle.setObjectName("dashboard-subtitle")
        self.root_layout.addWidget(subtitle)
        actions = QHBoxLayout()
        refresh_button = QPushButton("Refresh market data")
        refresh_button.setObjectName("primary-action")
        refresh_button.clicked.connect(self.refresh_market_data)
        actions.addWidget(refresh_button)
        inputs_button = QPushButton(
            "Hide model inputs" if self.inputs_visible else "Show model inputs"
        )
        inputs_button.clicked.connect(self.toggle_model_inputs)
        actions.addWidget(inputs_button)
        history_button = QPushButton("Review dossier history")
        history_button.clicked.connect(self.review_history)
        actions.addWidget(history_button)
        actions.addStretch()
        self.root_layout.addLayout(actions)

        tabs = QTabWidget()
        self.root_layout.addWidget(tabs, 1)
        overview_tab = QWidget()
        analysis_tab = QWidget()
        research_tab = QWidget()
        inputs_tab = QWidget()
        tabs.addTab(overview_tab, "Overview")
        tabs.addTab(analysis_tab, "Analysis")
        tabs.addTab(research_tab, "Research")
        tabs.addTab(inputs_tab, "Model inputs")
        overview_layout = QVBoxLayout(overview_tab)
        analysis_layout = QVBoxLayout(analysis_tab)
        research_layout = QVBoxLayout(research_tab)
        inputs_layout = QVBoxLayout(inputs_tab)
        for layout in (
            overview_layout,
            analysis_layout,
            research_layout,
            inputs_layout,
        ):
            layout.setContentsMargins(16, 16, 16, 16)
            layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout = overview_layout

        statuses = self.database.list_lifecycle_status_history(self.miner.id)
        if statuses:
            status = statuses[0]
            lifecycle_heading = QLabel("Lifecycle status")
            lifecycle_heading.setObjectName("section-heading")
            self.layout.addWidget(lifecycle_heading)
            status_detail = QLabel(f"{status.status}\nAs of {status.as_of_date} | {status.source}")
            status_detail.setObjectName("status-value")
            self.layout.addWidget(status_detail)
            update_status_button = QPushButton("Update lifecycle status")
            update_status_button.clicked.connect(lambda: self.update_lifecycle_status(status.status))
            self.layout.addWidget(update_status_button, alignment=Qt.AlignmentFlag.AlignLeft)

        milestones = self.database.list_milestones(self.miner.id)
        if milestones:
            milestones_heading = QLabel("Key milestones")
            milestones_heading.setObjectName("section-heading")
            self.layout.addWidget(milestones_heading)
            for milestone in milestones:
                detail = QLabel(
                    f"{milestone.category}: {milestone.title}\n"
                    f"{milestone.status} | {milestone.target_date}\n"
                    f"{milestone.detail}\n{milestone.source}"
                )
                detail.setWordWrap(True)
                self.layout.addWidget(detail)
                update_milestone_button = QPushButton("Record milestone outcome")
                update_milestone_button.clicked.connect(
                    lambda _, item=milestone: self.update_milestone(item.category, item.title)
                )
                self.layout.addWidget(
                    update_milestone_button, alignment=Qt.AlignmentFlag.AlignLeft
                )

        parameters = self.database.list_current_parameters(self.miner.id)
        market_snapshot = self.database.get_latest_market_snapshot(self.miner.id)
        trading_currency = self.miner.trading_currency
        usd_to_trading_rate = self._usd_to_currency_rate(trading_currency)
        self.layout = analysis_layout
        analysis_heading = QLabel("Current analysis")
        analysis_heading.setObjectName("section-heading")
        self.layout.addWidget(analysis_heading)
        analysis = self._calculate_analysis(parameters, market_snapshot)
        if analysis is None:
            self.layout.addWidget(
                QLabel("Analysis unavailable until market and model inputs are refreshed.")
            )
        elif usd_to_trading_rate is None:
            self.layout.addWidget(
            QLabel(f"Currency conversion unavailable for {trading_currency}.")
            )
        else:
            parameter_snapshots = {snapshot.parameter: snapshot for snapshot in parameters}
            parameter_values = {
                parameter: snapshot.value
                for parameter, snapshot in parameter_snapshots.items()
            }
            annual_production_snapshot = parameter_snapshots.get(
                "annual_production_ounces"
            )
            shares_snapshot = parameter_snapshots.get("basic_shares_outstanding")
            mine_life_snapshot = parameter_snapshots.get("mine_life_years")
            production_marker = (
                "§" if annual_production_snapshot is not None and shares_snapshot is not None else ""
            )
            shared_production_life_source = (
                annual_production_snapshot is not None
                and mine_life_snapshot is not None
                and annual_production_snapshot.source == mine_life_snapshot.source
                and annual_production_snapshot.as_of_date == mine_life_snapshot.as_of_date
            )
            lifetime_marker = (
                "§" if shared_production_life_source else "¶"
                if (
                    annual_production_snapshot is not None
                    and mine_life_snapshot is not None
                    and shares_snapshot is not None
                )
                else ""
            )
            metrics = QHBoxLayout()
            for label, value in (
                (f"Share price ({self._currency_symbol(market_snapshot.currency)})", self._format_currency_value(market_snapshot.price, market_snapshot.currency)),
                (
                    f"Annual margin / share ({self._currency_symbol(trading_currency)})",
                    self._format_currency_value(
                        analysis.annual_margin_usd_per_share * usd_to_trading_rate,
                        trading_currency,
                    ),
                ),
                (
                    "Lifetime margin / SP (x)",
                    self._format_ratio(analysis.lifetime_margin_to_price),
                ),
                ("AgEq price ($/AgEq oz)", self._format_currency_value(analysis.equivalent_price_usd_per_ounce, "USD", "‡")),
                ("Margin per AgEq oz ($)", self._format_currency_value(analysis.margin_usd_per_equivalent_ounce, "USD")),
                ("Annual AgEq oz / share (oz)", f"{analysis.annual_equivalent_ounces_per_share:,.4f}{production_marker}"),
                ("Lifetime AgEq oz / share (oz)", f"{analysis.lifetime_equivalent_ounces_per_share:,.4f}{lifetime_marker}"),
            ):
                metric = QWidget()
                metric.setFixedWidth(180)
                metric_layout = QVBoxLayout(metric)
                metric_layout.setContentsMargins(0, 0, 28, 8)
                metric_label = QLabel(label)
                metric_label.setObjectName("metric-label")
                metric_label.setToolTip(metric_explanation(label))
                metric_value = self._metric_value_widget(
                    value, metric_explanation(label)
                )
                metric_layout.addWidget(metric_label)
                metric_layout.addWidget(metric_value)
                metrics.addWidget(metric)
            metrics.addStretch()
            self.layout.addLayout(metrics)
            detailed_metrics = [
                (
                    f"Risked NAV / share ({self._currency_symbol(trading_currency)})",
                    "Unavailable"
                    if analysis.risked_nav_usd_per_share is None
                    else self._format_currency_value(
                        analysis.risked_nav_usd_per_share * usd_to_trading_rate,
                        trading_currency,
                        "*",
                    ),
                ),
                (
                    "Risked NAV / SP (x)",
                    "Unavailable"
                    if analysis.risked_nav_to_price is None
                    else self._format_ratio(analysis.risked_nav_to_price, "*"),
                ),
                (
                    f"NAV / share ({self._currency_symbol(trading_currency)})",
                    "Unavailable"
                    if analysis.equity_nav_usd_per_share is None
                    else self._format_currency_value(
                        analysis.equity_nav_usd_per_share * usd_to_trading_rate,
                        trading_currency,
                        "*",
                    ),
                ),
                (
                    "NAV / SP (x)",
                    "Unavailable"
                    if analysis.equity_nav_to_price is None
                    else self._format_ratio(analysis.equity_nav_to_price, "*"),
                ),
            ]
            if analysis.npv_usd_per_share is not None:
                detailed_metrics.extend(
                    [
                        (f"After-tax NPV / share ({self._currency_symbol(trading_currency)})", self._format_currency_value(analysis.npv_usd_per_share * usd_to_trading_rate, trading_currency, "*")),
                        ("NPV / SP (x)", self._format_ratio(analysis.npv_to_price, "*")),
                    ]
                )
            detailed_metrics.append(
                (f"Lifetime margin / share ({self._currency_symbol(trading_currency)})", self._format_currency_value(analysis.lifetime_margin_usd_per_share * usd_to_trading_rate, trading_currency))
            )
            results = QHBoxLayout()
            for index, (label, value) in enumerate(detailed_metrics):
                metric = QWidget()
                metric_layout = QVBoxLayout(metric)
                metric_layout.setContentsMargins(0, 8, 28, 8)
                metric_label = QLabel(label)
                metric_label.setObjectName("metric-label")
                metric_label.setToolTip(metric_explanation(label))
                metric_value = self._metric_value_widget(
                    value, metric_explanation(label)
                )
                metric_layout.addWidget(metric_label)
                metric_layout.addWidget(metric_value)
                metric.setFixedWidth(180)
                results.addWidget(metric)
            results.addStretch()
            self.layout.addLayout(results)
            aisc_snapshot = parameter_snapshots.get("aisc_per_ounce")
            if aisc_snapshot is not None:
                aisc_row = QHBoxLayout()
                aisc_metric = QWidget()
                aisc_metric.setFixedWidth(180)
                aisc_layout = QVBoxLayout(aisc_metric)
                aisc_layout.setContentsMargins(0, 8, 28, 8)
                aisc_label = QLabel("AISC ($/AgEq oz)")
                aisc_label.setObjectName("metric-label")
                aisc_label.setToolTip(metric_explanation("AISC"))
                aisc_value = self._metric_value_widget(
                    self._format_currency_value(aisc_snapshot.value, "USD", "†"),
                    metric_explanation("AISC"),
                )
                aisc_layout.addWidget(aisc_label)
                aisc_layout.addWidget(aisc_value)
                aisc_row.addWidget(aisc_metric)
                aisc_row.addStretch()
                self.layout.addLayout(aisc_row)
            resource_snapshot = parameter_snapshots.get("total_resource_equivalent_ounces")
            if analysis.resource_equivalent_ounces_per_share is not None:
                resource_row = QHBoxLayout()
                for label, value in (
                    (
                        "Resource AgEq oz / share (oz)",
                        f"{analysis.resource_equivalent_ounces_per_share:,.4f}#",
                    ),
                    (
                        "Resource margin / SP (x)",
                        self._format_ratio(analysis.resource_margin_to_price, "#"),
                    ),
                ):
                    metric = QWidget()
                    metric.setFixedWidth(180)
                    metric_layout = QVBoxLayout(metric)
                    metric_layout.setContentsMargins(0, 8, 28, 8)
                    metric_label = QLabel(label)
                    metric_label.setObjectName("metric-label")
                    metric_label.setToolTip(metric_explanation(label))
                    metric_value = self._metric_value_widget(
                        value, metric_explanation(label)
                    )
                    metric_layout.addWidget(metric_label)
                    metric_layout.addWidget(metric_value)
                    resource_row.addWidget(metric)
                resource_row.addStretch()
                self.layout.addLayout(resource_row)
            self._render_scenario_analysis(
                parameters, market_snapshot, analysis, trading_currency, usd_to_trading_rate
            )
            self.layout.addSpacing(12)
            study_prices = [
                (parameter.removeprefix("study_metal_price_").removesuffix("_usd_per_ounce"), value)
                for parameter, value in parameter_values.items()
                if re.fullmatch(r"study_metal_price_[a-z]+_usd_per_ounce", parameter)
            ]
            if analysis.npv_usd_per_share is not None and study_prices:
                assumptions = ", ".join(
                    f"{metal.title()} ${price:,.2f}/oz"
                    for metal, price in sorted(
                        study_prices,
                        key=lambda study_price: (
                            study_price[0] != self.miner.primary_commodity.lower(),
                            study_price[0],
                        ),
                    )
                )
                discount_rate = parameter_values.get("study_discount_rate_percent")
                discount_text = (
                    f"; {discount_rate:g}% discount rate" if discount_rate is not None else ""
                )
                npv_snapshot = parameter_snapshots.get("after_tax_npv_usd")
                source_text = (
                    f"; FS: {npv_snapshot.source} | As of {npv_snapshot.as_of_date}"
                    if npv_snapshot is not None
                    else ""
                )
                study_note = QLabel(f"* {assumptions}{discount_text}{source_text}.")
                study_note.setObjectName("analysis-note")
                study_note.setWordWrap(True)
                self.layout.addWidget(study_note)
            if aisc_snapshot is not None:
                aisc_note = QLabel(
                    f"† AISC source: {aisc_snapshot.source} | As of {aisc_snapshot.as_of_date}."
                )
                aisc_note.setObjectName("analysis-note")
                aisc_note.setWordWrap(True)
                self.layout.addWidget(aisc_note)
            if resource_snapshot is not None:
                resource_note = QLabel(
                    "# Resource screening uses total measured, indicated, and inferred "
                    "in-situ resources; it is not a reserve, mine plan, feasibility study, "
                    f"or NPV. Source: {resource_snapshot.source} "
                    f"| As of {resource_snapshot.as_of_date}."
                )
                resource_note.setObjectName("analysis-note")
                resource_note.setWordWrap(True)
                self.layout.addWidget(resource_note)
            metal_price_snapshots = [
                snapshot
                for parameter in parameter_snapshots
                if (match := re.fullmatch(r"annual_payable_([a-z]+)_ounces", parameter))
                and (snapshot := self.database.get_latest_commodity_price(match.group(1)))
            ]
            if metal_price_snapshots:
                prices_text = ", ".join(
                    f"{snapshot.commodity.title()} "
                    f"{self._format_currency_value(snapshot.price, snapshot.currency)}/oz"
                    for snapshot in sorted(
                        metal_price_snapshots,
                        key=lambda snapshot: (
                            snapshot.commodity != self.miner.primary_commodity.lower(),
                            snapshot.commodity,
                        ),
                    )
                )
                metal_price_note = QLabel(f"‡ AgEq metal prices: {prices_text}.")
                metal_price_note.setObjectName("analysis-note")
                metal_price_note.setWordWrap(True)
                self.layout.addWidget(metal_price_note)
            if annual_production_snapshot is not None and shares_snapshot is not None:
                production_note = QLabel(
                    "§ Annual AgEq oz / share sources: "
                    f"production: {annual_production_snapshot.source} "
                    f"| As of {annual_production_snapshot.as_of_date}."
                )
                production_note.setObjectName("analysis-note")
                production_note.setWordWrap(True)
                self.layout.addWidget(production_note)
            if (
                annual_production_snapshot is not None
                and mine_life_snapshot is not None
                and shares_snapshot is not None
                and not shared_production_life_source
            ):
                lifetime_note = QLabel(
                    "¶ Lifetime AgEq oz / share sources: "
                    f"production: {annual_production_snapshot.source} "
                    f"| As of {annual_production_snapshot.as_of_date}; "
                    f"mine life: {mine_life_snapshot.source} "
                    f"| As of {mine_life_snapshot.as_of_date}."
                )
                lifetime_note.setObjectName("analysis-note")
                lifetime_note.setWordWrap(True)
                self.layout.addWidget(lifetime_note)

        self.layout = inputs_layout
        self._render_model_inputs(parameters, market_snapshot)

        add_input_button = QPushButton("Add model input")
        add_input_button.clicked.connect(self.add_model_input)
        self.layout.addWidget(add_input_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.layout = research_layout
        research_heading = QLabel("Research timeline")
        research_heading.setObjectName("section-heading")
        self.layout.addWidget(research_heading)
        add_milestone_button = QPushButton("Add milestone")
        add_milestone_button.clicked.connect(self.add_milestone)
        self.layout.addWidget(add_milestone_button, alignment=Qt.AlignmentFlag.AlignLeft)
        add_note_button = QPushButton("Add research note")
        add_note_button.clicked.connect(self.add_research_note)
        self.layout.addWidget(add_note_button, alignment=Qt.AlignmentFlag.AlignLeft)
        entries = self.database.list_research_entries(self.miner.id)
        if entries:
            for entry in entries:
                detail = QLabel(f"{entry.entry_date}: {entry.note}\n{entry.source}")
                detail.setWordWrap(True)
                self.layout.addWidget(detail)
        else:
            self.layout.addWidget(QLabel("No research entries yet."))
        self.layout.addStretch()
        tabs.setCurrentIndex(min(self.active_tab, tabs.count() - 1))
        tabs.currentChanged.connect(self._set_active_tab)

    def _set_active_tab(self, index: int) -> None:
        self.active_tab = index

    def _calculate_analysis(self, parameters, market_snapshot, metal_prices=None):
        if market_snapshot is None:
            return None
        quote_price_usd = self._quote_price_usd(market_snapshot)
        if quote_price_usd is None:
            return None
        values = {parameter.parameter: parameter.value for parameter in parameters}
        metal_volumes = {
            parameter.removeprefix("annual_payable_").removesuffix("_ounces"): value
            for parameter, value in values.items()
            if parameter.startswith("annual_payable_") and parameter.endswith("_ounces")
        }
        if metal_prices is None:
            metal_prices = {}
            for metal in metal_volumes:
                price = self.database.get_latest_commodity_price(metal)
                if price is None or price.currency != "USD" or price.unit != "USD/oz":
                    return None
                metal_prices[metal] = price.price
        required = {
            "annual_production_ounces",
            "aisc_per_ounce",
            "mine_life_years",
            "basic_shares_outstanding",
        }
        if not metal_volumes or not required.issubset(values):
            return None
        return calculate_analysis(
            AnalysisInputs(
                annual_payable_metal_volumes=metal_volumes,
                metal_prices_usd=metal_prices,
                annual_equivalent_ounces=values["annual_production_ounces"],
                aisc_usd_per_equivalent_ounce=values["aisc_per_ounce"],
                mine_life_years=values["mine_life_years"],
                shares_outstanding=values["basic_shares_outstanding"],
                share_price_usd=quote_price_usd,
                total_resource_equivalent_ounces=values.get("total_resource_equivalent_ounces"),
                after_tax_npv_usd=values.get("after_tax_npv_usd"),
                cash_usd=values.get("cash_usd"),
                total_debt_usd=values.get("total_debt_usd"),
                development_risk_factor=self.development_risk_factor,
                additional_dilution_shares=self.additional_dilution_shares,
                potential_conversion_shares=values.get("potential_conversion_shares"),
            )
        )

    def _current_metal_prices(self, parameters) -> dict[str, float] | None:
        metals = {
            parameter.parameter.removeprefix("annual_payable_").removesuffix("_ounces")
            for parameter in parameters
            if parameter.parameter.startswith("annual_payable_")
            and parameter.parameter.endswith("_ounces")
        }
        prices = {}
        for metal in metals:
            price = self.database.get_latest_commodity_price(metal)
            if price is None or price.currency != "USD" or price.unit != "USD/oz":
                return None
            prices[metal] = price.price
        return prices

    def _render_scenario_analysis(
        self, parameters, market_snapshot, current, trading_currency: str, usd_to_trading_rate: float
    ) -> None:
        current_prices = self._current_metal_prices(parameters)
        if current_prices is None:
            return
        for metal, price in current_prices.items():
            self.scenario_prices.setdefault(metal, price)

        self.layout.addWidget(QLabel("Scenario metal prices"))
        controls = QFormLayout()
        for metal in sorted(current_prices):
            price_input = QDoubleSpinBox()
            price_input.setObjectName(f"scenario-price-{metal}")
            price_input.setRange(0.01, max(current_prices[metal] * 3, 10_000))
            price_input.setDecimals(0)
            price_input.setSingleStep({"gold": 100.0, "silver": 10.0}.get(metal, 1.0))
            price_input.setPrefix("$")
            price_input.setSuffix("/oz")
            price_input.setValue(self.scenario_prices[metal])
            price_input.editingFinished.connect(
                lambda input_widget=price_input, commodity=metal: self.set_scenario_price(
                    commodity, input_widget.value()
                )
            )
            reset_button = QPushButton("Reset")
            reset_button.setObjectName(f"scenario-reset-{metal}")
            reset_button.setToolTip(f"Restore the latest stored {metal} price")
            reset_button.clicked.connect(
                lambda _, commodity=metal, price=current_prices[metal]: self.reset_scenario_price(
                    commodity, price
                )
            )
            control = QWidget()
            control_layout = QHBoxLayout(control)
            control_layout.setContentsMargins(0, 0, 0, 0)
            control_layout.addWidget(price_input)
            control_layout.addWidget(reset_button)
            control_layout.addStretch()
            controls.addRow(metal.title(), control)
        self.layout.addLayout(controls)

        scenario = self._calculate_analysis(
            parameters, market_snapshot, self.scenario_prices
        )
        if scenario is None:
            return
        future_heading = QLabel("Future case")
        future_heading.setObjectName("section-heading")
        self.layout.addWidget(future_heading)
        future_metrics = QHBoxLayout()
        metrics = [
            ("Future AgEq price ($/AgEq oz)", self._format_currency_value(scenario.equivalent_price_usd_per_ounce, "USD")),
            (
                f"Future annual margin / share ({self._currency_symbol(trading_currency)})",
                self._format_currency_value(
                    scenario.annual_margin_usd_per_share * usd_to_trading_rate,
                    trading_currency,
                ),
            ),
            (
                f"Future lifetime margin / share ({self._currency_symbol(trading_currency)})",
                self._format_currency_value(
                    scenario.lifetime_margin_usd_per_share * usd_to_trading_rate,
                    trading_currency,
                ),
            ),
            ("Future lifetime margin / SP (x)", self._format_ratio(scenario.lifetime_margin_to_price)),
        ]
        if scenario.resource_margin_to_price is not None:
            metrics.append(
                (
                    "Future resource margin / SP (x)",
                    self._format_ratio(scenario.resource_margin_to_price, "#"),
                )
            )
        for label, value in metrics:
            metric = QWidget()
            metric_layout = QVBoxLayout(metric)
            metric_layout.setContentsMargins(0, 0, 28, 8)
            metric_label = QLabel(label)
            metric_label.setObjectName("metric-label")
            metric_label.setToolTip(metric_explanation(label))
            metric_value = self._metric_value_widget(value, metric_explanation(label))
            metric_layout.addWidget(metric_label)
            metric_layout.addWidget(metric_value)
            future_metrics.addWidget(metric)
        future_metrics.addStretch()
        self.layout.addLayout(future_metrics)

    def _render_risked_nav_analysis(
        self, analysis, trading_currency: str, usd_to_trading_rate: float
    ) -> None:
        if analysis.equity_nav_usd_per_share is None:
            return
        self.layout.addWidget(QLabel("Risked NAV scenario"))
        risk_input = QDoubleSpinBox()
        risk_input.setRange(1, 100)
        risk_input.setDecimals(0)
        risk_input.setSuffix("%")
        risk_input.setValue(self.development_risk_factor * 100)
        risk_input.valueChanged.connect(
            lambda value: self.set_development_risk_factor(value / 100)
        )
        risk_slider = QSlider(Qt.Orientation.Horizontal)
        risk_slider.setRange(1, 100)
        risk_slider.setValue(round(self.development_risk_factor * 100))
        risk_slider.valueChanged.connect(
            lambda value: self.set_development_risk_factor(value / 100)
        )
        control = QWidget()
        control_layout = QHBoxLayout(control)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.addWidget(risk_slider)
        control_layout.addWidget(risk_input)
        controls = QFormLayout()
        controls.addRow("Development risk factor", control)
        self.layout.addLayout(controls)

        results = QFormLayout()
        results.addRow(
            "Risked NAV / share",
            QLabel(
                self._format_currency(
                    analysis.risked_nav_usd_per_share,
                    trading_currency,
                    usd_to_trading_rate,
                )
            ),
        )
        results.addRow(
            "Risked NAV / SP", QLabel(f"{analysis.risked_nav_to_price:,.2f}x")
        )
        self.layout.addLayout(results)

    def set_scenario_price(self, commodity: str, price: float) -> None:
        self.scenario_prices[commodity] = price
        self.render()

    def reset_scenario_price(self, commodity: str, price: float) -> None:
        self.set_scenario_price(commodity, price)

    def set_development_risk_factor(self, risk_factor: float) -> None:
        self.development_risk_factor = risk_factor
        self.render()

    def _render_dilution_analysis(
        self, analysis, trading_currency: str, usd_to_trading_rate: float
    ) -> None:
        if analysis.diluted_equity_nav_usd_per_share is None:
            return
        self.layout.addWidget(QLabel("Dilution scenario"))
        dilution_input = QDoubleSpinBox()
        dilution_input.setRange(0, 10_000_000_000)
        dilution_input.setDecimals(0)
        dilution_input.setSingleStep(1_000_000)
        dilution_input.setSuffix(" shares")
        dilution_input.setValue(self.additional_dilution_shares)
        dilution_input.valueChanged.connect(self.set_additional_dilution_shares)
        controls = QFormLayout()
        controls.addRow("Additional shares", dilution_input)
        self.layout.addLayout(controls)

        results = QFormLayout()
        results.addRow(
            "Shares after dilution",
            QLabel(f"{analysis.diluted_shares_outstanding:,.0f}"),
        )
        results.addRow(
            "Diluted NAV per share",
            QLabel(
                self._format_currency(
                    analysis.diluted_equity_nav_usd_per_share,
                    trading_currency,
                    usd_to_trading_rate,
                )
            ),
        )
        if analysis.diluted_risked_nav_usd_per_share is not None:
            results.addRow(
                "Diluted risked NAV per share",
                QLabel(
                    self._format_currency(
                        analysis.diluted_risked_nav_usd_per_share,
                        trading_currency,
                        usd_to_trading_rate,
                    )
                ),
            )
        self.layout.addLayout(results)

        if analysis.fully_converted_equity_nav_usd_per_share is not None:
            self.layout.addWidget(
                QLabel("Illustrative full conversion (debt treatment unchanged)")
            )
            conversion_results = QFormLayout()
            conversion_results.addRow(
                "Shares after full conversion",
                QLabel(f"{analysis.fully_converted_shares_outstanding:,.0f}"),
            )
            conversion_results.addRow(
                "Full-conversion NAV per share",
                QLabel(
                    self._format_currency(
                        analysis.fully_converted_equity_nav_usd_per_share,
                        trading_currency,
                        usd_to_trading_rate,
                    )
                ),
            )
            if analysis.fully_converted_risked_nav_usd_per_share is not None:
                conversion_results.addRow(
                    "Full-conversion risked NAV per share",
                    QLabel(
                        self._format_currency(
                            analysis.fully_converted_risked_nav_usd_per_share,
                            trading_currency,
                            usd_to_trading_rate,
                        )
                    ),
                )
            self.layout.addLayout(conversion_results)

    def set_additional_dilution_shares(self, shares: float) -> None:
        self.additional_dilution_shares = shares
        self.render()

    def _render_saved_scenarios(self) -> None:
        self.layout.addWidget(QLabel("Saved scenarios"))
        scenarios = self.database.list_analysis_scenarios(self.miner.id)
        if scenarios:
            scenario_input = QComboBox()
            scenario_input.addItem("Load saved scenario", None)
            for scenario in scenarios:
                scenario_input.addItem(scenario.name, scenario.id)
            scenario_input.activated.connect(
                lambda index: self.load_analysis_scenario(scenario_input.itemData(index))
            )
            self.layout.addWidget(scenario_input)
        save_button = QPushButton("Save current scenario")
        save_button.clicked.connect(self.save_analysis_scenario)
        self.layout.addWidget(save_button, alignment=Qt.AlignmentFlag.AlignLeft)

    def save_analysis_scenario(self) -> None:
        dialog = SaveScenarioDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.add_analysis_scenario(
                self.miner.id,
                dialog.value(),
                self.scenario_prices,
                self.development_risk_factor,
            )
            self.render()

    def load_analysis_scenario(self, scenario_id: int | None) -> None:
        if scenario_id is None:
            return
        scenario = self.database.get_analysis_scenario(scenario_id)
        if scenario is None or scenario.miner_id != self.miner.id:
            return
        self.scenario_prices = dict(scenario.metal_prices_usd)
        self.development_risk_factor = scenario.development_risk_factor
        self.render()

    def _usd_to_currency_rate(self, currency: str) -> float | None:
        if currency == "USD":
            return 1.0
        rate = self.database.get_latest_exchange_rate("USD", currency)
        if rate is None or rate.rate <= 0:
            return None
        return rate.rate

    def _quote_price_usd(self, market_snapshot) -> float | None:
        quote_to_usd_rate = self._usd_to_currency_rate(market_snapshot.currency)
        if quote_to_usd_rate is None:
            return None
        return market_snapshot.price / quote_to_usd_rate

    @staticmethod
    def _format_currency(value_usd: float, currency: str, usd_to_currency_rate: float) -> str:
        return MinerDashboard._format_currency_value(value_usd * usd_to_currency_rate, currency)

    @staticmethod
    def _metric_value_widget(value: str, tooltip: str) -> QWidget:
        marker = value[-1] if value and value[-1] in "*†‡§¶#" else ""
        value_label = QLabel(value[:-1] if marker else value)
        value_label.setObjectName("metric-value")
        value_label.setToolTip(tooltip)
        if not marker:
            return value_label
        value_widget = QWidget()
        value_layout = QHBoxLayout(value_widget)
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setSpacing(2)
        marker_label = QLabel(marker)
        marker_label.setObjectName("metric-marker")
        marker_label.setToolTip(tooltip)
        value_layout.addWidget(value_label)
        value_layout.addWidget(marker_label)
        value_layout.addStretch()
        return value_widget

    @staticmethod
    def _format_currency_value(value: float, currency: str, marker: str = "") -> str:
        return f"{value:,.2f} {MinerDashboard._currency_symbol(currency)}{marker}"

    @staticmethod
    def _currency_symbol(currency: str) -> str:
        symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
            "CAD": "C$",
            "AUD": "A$",
            "SEK": "kr",
        }
        return symbols.get(currency.upper(), currency.upper())

    @staticmethod
    def _format_ratio(value: float, marker: str = "") -> str:
        return f"{value:,.2f}x{marker}"

    def _render_model_inputs(self, parameters, market_snapshot) -> None:
        self.layout.addWidget(QLabel("Model inputs"))
        form = QFormLayout()
        for parameter in parameters:
            name = parameter.parameter.replace("_", " ").title()
            value = f"{parameter.value:,.12g} {parameter.unit}"
            detail = QLabel(f"{value}\nAs of {parameter.as_of_date} | {parameter.source}")
            detail.setWordWrap(True)
            form.addRow(name, detail)
        if market_snapshot:
            detail = QLabel(
                f"{market_snapshot.price:,.12g} {market_snapshot.currency}\n"
                f"Retrieved {market_snapshot.retrieved_at} | {market_snapshot.source}"
            )
            detail.setWordWrap(True)
            form.addRow("Share price", detail)
        for commodity in ("silver", "gold"):
            price = self.database.get_latest_commodity_price(commodity)
            if price:
                detail = QLabel(
                    f"{price.price:,.12g} {price.unit}\n"
                    f"Retrieved {price.retrieved_at} | {price.source}"
                )
                detail.setWordWrap(True)
                form.addRow(f"{commodity.title()} price", detail)
        self.layout.addLayout(form)

        self.layout.addWidget(QLabel("FX rates"))
        display_setting = self.database.get_current_application_setting(BASE_CURRENCY.key)
        display_currency = (
            display_setting.value if display_setting is not None else BASE_CURRENCY.default_value
        )
        pairs = {
            ("USD", self.miner.trading_currency),
            (self.miner.trading_currency, display_currency),
        }
        for from_currency, to_currency in sorted(pairs):
            if from_currency == to_currency:
                continue
            rate = self.database.get_latest_exchange_rate(from_currency, to_currency)
            if rate:
                self.layout.addWidget(
                    QLabel(f"1 {from_currency} = {rate.rate:,.12g} {to_currency}")
                )
            else:
                self.layout.addWidget(
                    QLabel(f"No {from_currency}/{to_currency} rate yet.")
                )

    def toggle_model_inputs(self) -> None:
        self.active_tab = 3
        self.render()

    def refresh_market_data(self) -> None:
        try:
            refresh_market_data(self.database, self.miner)
        except Exception as error:
            QMessageBox.warning(self, "Market data unavailable", str(error))
            return
        self.render()

    def add_research_note(self) -> None:
        dialog = AddResearchEntryDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.add_research_entry(self.miner.id, *dialog.values())
            self.render()

    def add_model_input(self) -> None:
        dialog = AddModelInputDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.add_parameter_snapshot(self.miner.id, *dialog.values())
            self.render()

    def update_lifecycle_status(self, current_status: str) -> None:
        dialog = UpdateLifecycleStatusDialog(current_status, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.add_lifecycle_status_snapshot(self.miner.id, *dialog.values())
            self.render()

    def update_milestone(self, category: str, title: str) -> None:
        dialog = UpdateMilestoneDialog(category, title, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.add_milestone(self.miner.id, *dialog.values())
            self.render()

    def review_history(self) -> None:
        HistoryDialog(self.database, self.miner, self).exec()

    def add_milestone(self) -> None:
        dialog = AddMilestoneDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.add_milestone(self.miner.id, *dialog.values())
            self.render()


class MainWindow(QMainWindow):
    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database
        self.setWindowTitle("Gosimine")
        self.resize(1280, 800)
        self.detail_scroll: QScrollArea | None = None

        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["Selected miners"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().hide()
        self.table.verticalHeader().hide()
        self.table.setMaximumWidth(240)
        self.table.itemSelectionChanged.connect(self.show_selected_miner)

        self.detail = QLabel("Select a miner to view its research workspace.")
        self.detail.setWordWrap(True)
        self.detail.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.detail.setContentsMargins(24, 24, 24, 24)

        self.splitter = QSplitter()
        self.splitter.addWidget(self.table)
        self.splitter.addWidget(self.detail)
        self.splitter.setSizes([220, 880])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        add_button = QPushButton("Add miner")
        add_button.clicked.connect(self.add_miner)
        catalog_button = QPushButton("Browse catalog")
        catalog_button.clicked.connect(self.select_catalog_miner)
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self.open_settings)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        actions = QHBoxLayout()
        actions.addWidget(add_button)
        actions.addWidget(catalog_button)
        actions.addWidget(settings_button)
        actions.addStretch()
        layout.addLayout(actions)
        layout.addWidget(self.splitter)

        central_widget = QWidget()
        central_widget.setObjectName("workspace")
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        self.refresh_miners()

    def refresh_miners(self) -> None:
        miners = self.database.list_miners()
        self.table.setRowCount(len(miners))
        for row, miner in enumerate(miners):
            item = QTableWidgetItem(f"{miner.ticker}: {miner.name}")
            item.setData(Qt.ItemDataRole.UserRole, miner)
            self.table.setItem(row, 0, item)
        if miners:
            self.table.selectRow(0)

    def show_selected_miner(self) -> None:
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
        miner = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if isinstance(miner, Miner):
            dashboard = MinerDashboard(self.database, miner)
            detail_scroll = QScrollArea()
            detail_scroll.setWidgetResizable(True)
            detail_scroll.setMinimumWidth(480)
            detail_scroll.setWidget(dashboard)
            previous_detail = self.splitter.replaceWidget(1, detail_scroll)
            self.detail_scroll = detail_scroll
            self.detail = dashboard
            self.splitter.setSizes([220, 880])
            previous_detail.deleteLater()

    def add_miner(self) -> None:
        dialog = AddMinerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.add_miner(*dialog.values())
            self.refresh_miners()

    def select_catalog_miner(self) -> None:
        dialog = CatalogDialog(self.database, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_ticker is not None:
            self.database.select_catalog_miner(dialog.selected_ticker)
            self.refresh_miners()

    def open_settings(self) -> None:
        if SettingsDialog(self.database, self).exec() == QDialog.DialogCode.Accepted:
            if isinstance(self.detail, MinerDashboard):
                self.detail.render()


def main() -> None:
    application = QApplication(sys.argv)
    application.setStyleSheet(APPLICATION_STYLE)
    database_path = Path("data") / "gosimine.sqlite3"
    initialize_database(database_path, Path("seed") / "miners.json")
    database = Database(database_path)
    window = MainWindow(database)
    window.show()
    exit_code = application.exec()
    database.close()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()

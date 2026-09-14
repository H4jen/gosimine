from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from matplotlib import mathtext
from matplotlib.font_manager import FontProperties
from PySide6.QtCore import QDate, QTimer, Qt
from PySide6.QtGui import QColor, QImage, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
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

from gosimine.database import Database, Miner, ParameterSnapshot
from gosimine.market_data import refresh_market_data
from gosimine.commodities import COMMODITIES
from gosimine.seed import initialize_database
from gosimine.analysis import (
    AnalysisInputs,
    ProjectInputs,
    calculate_analysis,
    consolidate_project_inputs,
)
from gosimine.settings import (
    APPLICATION_SETTINGS,
    BASE_CURRENCY,
    DEFAULT_SCENARIO_GOLD_PRICE,
    DEFAULT_SCENARIO_SILVER_PRICE,
    TEXT_SIZE,
)


PARAMETER_UNITS = {
    "annual_production_ounces": "AgEq oz/year",
    "measured_indicated_resource_equivalent_ounces": "AgEq oz",
    "inferred_resource_equivalent_ounces": "AgEq oz",
    "total_resource_equivalent_ounces": "AgEq oz",
    "aisc_per_ounce": "USD/AgEq oz",
    "mine_life_years": "years",
    "after_tax_npv_usd": "USD",
    "cash_usd": "USD",
    "total_debt_usd": "USD",
    "potential_conversion_shares": "shares",
    "potential_dilution_shares": "shares",
    "basic_shares_outstanding": "shares",
    "study_discount_rate_percent": "%",
}

METRIC_EXPLANATIONS = {
    "Share price": "Latest market price for this listing. Source: the latest stored market snapshot.",
    "Risked NAV / share": "NAV per selected share count multiplied by the investor-entered development risk factor.",
    "Risked NAV / SP": "Risked NAV per selected share count divided by the current share price. Above 1.0x means the risked screening value exceeds the share price.",
    "NAV / share": "After-tax project NPV plus cash minus total debt, divided by the selected share count.",
    "NAV / SP": "NAV per selected share count divided by the current share price. Above 1.0x means the NAV estimate exceeds the share price.",
    "Annual margin / share": "Annual equivalent-metal production multiplied by current margin per equivalent-metal ounce, divided by the selected share count. This is an operating proxy, not EPS.",
    "Lifetime margin / SP": "Undiscounted lifetime operating-margin proxy per share divided by current share price. It is not project NPV or earnings.",
    "AISC": "Reported all-in sustaining cost per equivalent-metal ounce. It is the cost input subtracted from the equivalent-metal price to calculate the margin proxy.",
    "Mine life": "Sourced mine-life input used to calculate lifetime ounce and margin proxies. It may be project-specific or a temporary estimate; review its source and as-of date.",
    "AgEq price": "Payable-metal volumes valued at the latest stored metal prices, expressed per equivalent-metal ounce.",
    "Margin per AgEq oz": "AgEq price minus reported AISC. It is a screening margin, not reported net income.",
    "Annual AgEq oz / share": "Annual equivalent-metal production divided by the selected share count.",
    "Lifetime AgEq oz / share": "Annual equivalent-metal production multiplied by mine life, divided by the selected share count.",
    "Lifetime margin / share": "Annual operating-margin proxy per share multiplied by mine life. It is undiscounted.",
    "Resource AgEq oz / share": "Total measured, indicated, and inferred equivalent-metal resources divided by the selected share count. These are in-situ resource ounces, not a mine plan or reserves.",
    "Resource margin / SP": "Total resource equivalent-metal ounces per share multiplied by the current margin per equivalent-metal ounce, divided by share price. It is a speculative resource screening ratio, not NPV or expected profit.",
    "After-tax NPV / share": "Company-reported after-tax feasibility-study NPV divided by the selected share count. Review its source and study metal-price assumptions in Model inputs.",
    "NPV / SP": "After-tax study NPV per selected share count divided by the current share price. Above 1.0x means the study NPV estimate exceeds the share price.",
    "Future AgEq price": "Scenario payable-metal prices expressed per equivalent-metal ounce. This is a personal scenario, not a sourced market fact.",
    "Future annual margin / share": "Scenario annual operating-margin proxy per selected share count.",
    "Future lifetime margin / share": "Scenario undiscounted lifetime operating-margin proxy per selected share count.",
    "Future lifetime margin / SP": "Scenario lifetime operating-margin proxy per share divided by current share price.",
    "Future resource margin / SP": "Scenario total resource equivalent-metal ounces per share multiplied by scenario margin per equivalent-metal ounce, divided by share price. It is a speculative resource screening ratio, not NPV or expected profit.",
}

def render_math_formula(formula: str) -> QPixmap:
    parsed = mathtext.MathTextParser("agg").parse(
        formula,
        dpi=180,
        prop=FontProperties(size=14, math_fontfamily="cm"),
    )
    alpha_buffer = memoryview(parsed.image)
    height, width = alpha_buffer.shape
    alpha = alpha_buffer.tobytes()
    pixel_count = width * height
    pixels = bytearray(pixel_count * 4)
    pixels[0::4] = bytes([24]) * pixel_count
    pixels[1::4] = bytes([49]) * pixel_count
    pixels[2::4] = bytes([40]) * pixel_count
    pixels[3::4] = alpha
    image = QImage(bytes(pixels), width, height, width * 4, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(image.copy())


METRIC_GUIDES = {
    "AgEq price": (r"$P_{AgEq}=\frac{V}{Q}$", r"$P_{AgEq}=\frac{1{,}016}{17.383}=\$58.47/\mathrm{AgEq\ oz}$"),
    "Margin per AgEq oz": (r"$M_{AgEq}=P_{AgEq}-C$", r"$M_{AgEq}=\$58.47-\$10.61=\$47.86/\mathrm{AgEq\ oz}$"),
    "AISC": (r"$C=\mathrm{AISC}$", r"$C=\$10.61/\mathrm{AgEq\ oz}$"),
    "Annual AgEq oz / share": (r"$q=\frac{Q}{S}$", r"$q=\frac{17.383}{355.057}=0.0490\ \mathrm{AgEq\ oz/share}$"),
    "Lifetime AgEq oz / share": (r"$q_L=\frac{Q\times L}{S}$", r"$q_L=\frac{17.383\times9.4}{355.057}=0.4602\ \mathrm{AgEq\ oz/share}$"),
    "Annual margin / share": (r"$m=M_{AgEq}\times q$", r"$m=\$47.86\times0.0490=\$2.34/\mathrm{share}$"),
    "Lifetime margin / share": (r"$m_L=m\times L$", r"$m_L=\$2.34\times9.4=\$22.02/\mathrm{share}$"),
    "Lifetime margin / SP": (r"$\frac{m_L}{P}$", r"$\frac{22.02}{3.97}=5.55\times$"),
    "Resource AgEq oz / share": (r"$r=\frac{R}{S}$", r"$r=\frac{361.1}{355.057}=1.0170\ \mathrm{AgEq\ oz/share}$"),
    "Resource margin / SP": (r"$\frac{r\times M_{AgEq}}{P}$", r"$\frac{1.0170\times47.86}{3.97}=12.26\times$"),
    "After-tax NPV / share": (r"$\frac{N}{S}$", r"$\frac{\$1{,}802}{355.057}=\$5.08/\mathrm{share}$"),
    "NPV / SP": (r"$\frac{N/S}{P}$", r"$\frac{5.08}{3.97}=1.28\times$"),
    "NAV / share": (r"$\frac{N+K-D}{S}$", r"$\frac{\$1{,}802+\$406-\$240}{355.057}=\$5.54/\mathrm{share}$"),
    "NAV / SP": (r"$\frac{\mathrm{NAV}/S}{P}$", r"$\frac{5.54}{3.97}=1.40\times$"),
    "Risked NAV / share": (r"$\frac{\mathrm{NAV}}{S}\times f$", r"$\$5.54\times0.70=\$3.88/\mathrm{share}$"),
    "Risked NAV / SP": (r"$\frac{\mathrm{Risked\ NAV}/S}{P}$", r"$\frac{3.88}{3.97}=0.98\times$"),
    "Future AgEq price": (r"$P_{AgEq}^{\prime}=\frac{V^{\prime}}{Q}$", r"$P_{AgEq}^{\prime}=\frac{\$1{,}200}{17.383}=\$69.03/\mathrm{AgEq\ oz}$"),
    "Future annual margin / share": (r"$m^{\prime}=(P_{AgEq}^{\prime}-C)\times q$", r"$m^{\prime}=(\$69.03-\$10.61)\times0.0490=\$2.86/\mathrm{share}$"),
    "Future lifetime margin / share": (r"$m_L^{\prime}=m^{\prime}\times L$", r"$m_L^{\prime}=\$2.86\times9.4=\$26.88/\mathrm{share}$"),
    "Future lifetime margin / SP": (r"$\frac{m_L^{\prime}}{P}$", r"$\frac{26.88}{3.97}=6.77\times$"),
    "Future resource margin / SP": (r"$\frac{r\times(P_{AgEq}^{\prime}-C)}{P}$", r"$\frac{1.0170\times(69.03-10.61)}{3.97}=14.96\times$"),
}

METRIC_PURPOSES = {
    "AgEq price": "Why it matters: It converts a mixed gold-and-silver production profile into one comparable revenue price per equivalent ounce.",
    "Margin per AgEq oz": "Why it matters: It estimates the operating room between current metal prices and reported sustaining cost before corporate costs, tax, and financing.",
    "AISC": "Why it matters: It is the cost baseline used to judge sensitivity to metal prices and operating profitability.",
    "Annual AgEq oz / share": "Why it matters: It shows how much annual equivalent-metal production supports each existing share.",
    "Lifetime AgEq oz / share": "Why it matters: It connects the mine plan's total operating output to the current share count.",
    "Annual margin / share": "Why it matters: It turns the annual operating-margin proxy into a per-share figure that can be compared across companies.",
    "Lifetime margin / share": "Why it matters: It summarizes undiscounted mine-plan operating margin per share over the stated mine life.",
    "Lifetime margin / SP": "Why it matters: It compares the undiscounted lifetime operating-margin proxy with the price paid for one share.",
    "Resource AgEq oz / share": "Why it matters: It screens the in-situ resource endowment backing each share, separate from the reserve-backed mine plan.",
    "Resource margin / SP": "Why it matters: It is a high-level measure of how much resource-scale operating-margin potential is implied by the current share price.",
    "After-tax NPV / share": "Why it matters: It puts the study's after-tax project value on a per-share basis before balance-sheet adjustments.",
    "NPV / SP": "Why it matters: It compares feasibility-study project value per share with the current market price; above 1x indicates NPV exceeds price.",
    "NAV / share": "Why it matters: It adds cash and subtracts debt from project NPV to estimate value attributable to each basic share.",
    "NAV / SP": "Why it matters: It compares balance-sheet-adjusted NAV per share with the market price; above 1x indicates NAV exceeds price.",
    "Risked NAV / share": "Why it matters: It applies a user-selected development risk factor to NAV, recognizing execution and permitting uncertainty.",
    "Risked NAV / SP": "Why it matters: It compares risk-adjusted NAV per share with the market price; above 1x indicates risked NAV exceeds price.",
    "Future AgEq price": "Why it matters: It shows how the blended equivalent-metal price changes under your own gold and silver price scenario.",
    "Future annual margin / share": "Why it matters: It translates the scenario metal-price view into a per-share annual operating-margin proxy.",
    "Future lifetime margin / share": "Why it matters: It extends the scenario annual margin across the mine life to show its undiscounted per-share effect.",
    "Future lifetime margin / SP": "Why it matters: It compares the scenario lifetime margin proxy with today's share price.",
    "Future resource margin / SP": "Why it matters: It tests how a metal-price scenario changes the speculative resource-scale margin relative to the share price.",
}

METRIC_VARIABLES = {
    "Share price": "P = share price.",
    "AgEq price": "P_AgEq = equivalent-metal price; V = annual payable-metal value; Q = annual AgEq production.",
    "Margin per AgEq oz": "M_AgEq = margin per AgEq oz; P_AgEq = equivalent-metal price; C = AISC.",
    "AISC": "C = all-in sustaining cost per AgEq oz.",
    "Annual AgEq oz / share": "q = annual AgEq oz per share; Q = annual AgEq production; S = basic shares.",
    "Lifetime AgEq oz / share": "q_L = lifetime AgEq oz per share; Q = annual AgEq production; L = mine life; S = basic shares.",
    "Annual margin / share": "m = annual margin per share; M_AgEq = margin per AgEq oz; q = annual AgEq oz per share.",
    "Lifetime margin / share": "m_L = lifetime margin per share; m = annual margin per share; L = mine life.",
    "Lifetime margin / SP": "m_L = lifetime margin per share; P = share price.",
    "Resource AgEq oz / share": "r = resource AgEq oz per share; R = total AgEq resources; S = basic shares.",
    "Resource margin / SP": "r = resource AgEq oz per share; M_AgEq = margin per AgEq oz; P = share price.",
    "After-tax NPV / share": "N = after-tax NPV; S = basic shares.",
    "NPV / SP": "N = after-tax NPV; S = basic shares; P = share price.",
    "NAV / share": "N = after-tax NPV; K = cash; D = debt; S = basic shares.",
    "NAV / SP": "NAV = net asset value; S = basic shares; P = share price.",
    "Risked NAV / share": "NAV = net asset value; S = basic shares; f = development risk factor.",
    "Risked NAV / SP": "Risked NAV = NAV after applying the risk factor; S = basic shares; P = share price.",
    "Future AgEq price": "P'_AgEq = scenario equivalent-metal price; V' = scenario payable-metal value; Q = annual AgEq production.",
    "Future annual margin / share": "m' = scenario annual margin per share; P'_AgEq = scenario equivalent-metal price; C = AISC; q = annual AgEq oz per share.",
    "Future lifetime margin / share": "m'_L = scenario lifetime margin per share; m' = scenario annual margin per share; L = mine life.",
    "Future lifetime margin / SP": "m'_L = scenario lifetime margin per share; P = share price.",
    "Future resource margin / SP": "r = resource AgEq oz per share; P'_AgEq = scenario equivalent-metal price; C = AISC; P = share price.",
}

VARIABLE_GUIDES = (
    ("P", "Share price", "The latest quoted price for one share of the selected listing, in its trading currency. Example: P = $3.97/share."),
    ("V", "Annual payable-metal value", "The value of one year's payable metal output at the current metal prices. Example: V = $1,016M/year."),
    ("V'", "Scenario payable-metal value", "The same annual payable-metal value recalculated using the scenario metal prices. Example: V' changes when a gold or silver scenario is edited."),
    ("Q", "Annual AgEq production", "One year's payable production expressed as silver-equivalent ounces. Example: Q = 17.383M AgEq oz/year."),
    ("S", "Basic shares", "Current basic shares outstanding. Per-share values use S before optional dilution adjustments. Example: S = 355.057M shares."),
    ("L", "Mine life", "The mine-plan operating period in years. Example: L = 9.4 years."),
    ("C", "AISC", "All-in sustaining cost per equivalent-metal ounce, subtracted from the AgEq price to form the operating-margin proxy. Example: C = $10.61/AgEq oz."),
    ("R", "Total AgEq resources", "Combined measured, indicated, and inferred in-situ silver-equivalent resources. This is not a reserve or mine plan. Example: R = 361.1M AgEq oz."),
    ("N", "After-tax NPV", "Company-reported after-tax project NPV from the feasibility study. Example: N = $1.802B."),
    ("K", "Cash", "Reported cash and cash equivalents. Example: K = $406M."),
    ("D", "Debt", "Reported total debt. Example: D = $240M."),
    ("f", "Development risk factor", "The investor-entered probability factor applied to NAV. Example: f = 0.70 means 70%."),
    ("P_AgEq", "AgEq price", "Payable metal value divided by annual AgEq production. Example: P_AgEq = $58.47/AgEq oz."),
    ("M_AgEq", "Margin per AgEq oz", "AgEq price less AISC; it is an operating-margin proxy, not net income. Example: M_AgEq = $47.86/AgEq oz."),
    ("q and q_L", "AgEq ounces per share", "q is annual AgEq oz/share and q_L is lifetime AgEq oz/share. Example: q = 0.0490 and q_L = 0.4602 AgEq oz/share."),
    ("m and m_L", "Margin per share", "m is annual operating margin per share and m_L is lifetime undiscounted margin per share. Example: m = $2.34/share and m_L = $22.02/share."),
    ("r", "Resource AgEq oz per share", "Total AgEq resources divided by basic shares; it is a resource-screening measure. Example: r = 1.0170 AgEq oz/share."),
    ("NAV", "Net asset value", "After-tax NPV plus cash minus debt. Example: NAV = $1.968B, or $5.54/share before risk adjustment."),
    ("Primes (')", "Scenario values", "A prime marks a value recalculated with the scenario metal prices. Example: P'_AgEq is the scenario AgEq price and m' is scenario annual margin per share."),
)

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

TEXT_SIZE_POINTS = {"Default": 15, "Large": 17, "Extra large": 19}
METRIC_WIDTH = 205


def application_style(text_size: str = TEXT_SIZE.default_value) -> str:
    base_size = TEXT_SIZE_POINTS.get(text_size, TEXT_SIZE_POINTS[TEXT_SIZE.default_value])
    return """
QMainWindow { background: #d7e0d9; color: #1c2822; }
QWidget#workspace { background: #d7e0d9; }
QDialog { background: #ffffff; border: 2px solid #216b4d; color: #1c2822; }
QWidget { font-family: "Noto Sans", "DejaVu Sans", sans-serif; font-size: {base_size}px; }
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
QLabel#dashboard-title { color: #183128; font-size: {title_size}px; font-weight: 700; }
QLabel#dashboard-subtitle { color: #5a6b61; }
QLabel#section-heading {
    border-top: 1px solid #d4ddd6; color: #216b4d; font-size: {heading_size}px; font-weight: 700;
    margin-top: 12px; padding-top: 12px;
}
QLabel#status-value {
    background: #e2eee6; border: 1px solid #c4d7ca; border-radius: 4px;
    color: #1f583f; font-weight: 600; padding: 8px;
}
QLabel#notation-heading { color: #216b4d; font-size: {heading_size}px; font-weight: 700; }
QLabel#notation-text { color: #1c2822; font-size: {base_size}px; }
QLabel#metric-guide-title { color: #1c2822; font-size: {guide_size}px; font-weight: 600; }
QLabel#math-formula, QLabel#math-example {
    background: transparent; border: 0; color: #183128; padding: 4px 0;
}
QLabel#metric-label {
    color: #1c2822; font-size: {base_size}px; min-height: 42px;
    qproperty-wordWrap: true;
}
QLabel#metric-value { color: #17365d; font-size: {metric_value_size}px; font-weight: 700; }
QLabel#metric-marker { color: #1c2822; font-size: {base_size}px; font-weight: 400; }
QLabel#analysis-note { color: #1c2822; font-size: {base_size}px; }
QTabWidget::pane { border: 1px solid #cdd6cf; background: white; }
QTabBar::tab { padding: 7px 12px; }
""".replace("{base_size}", str(base_size)).replace(
        "{title_size}", str(base_size + 13)
    ).replace("{heading_size}", str(base_size + 3)).replace(
        "{guide_size}", str(base_size + 1)
    ).replace("{metric_value_size}", str(base_size + 9))


def apply_application_style(database: Database) -> None:
    application = QApplication.instance()
    if application is None:
        return
    setting = database.get_current_application_setting(TEXT_SIZE.key)
    text_size = setting.value if setting is not None else TEXT_SIZE.default_value
    application.setStyleSheet(application_style(text_size))


def is_supported_parameter(parameter: str) -> bool:
    return (
        parameter in PARAMETER_UNITS
        or bool(re.fullmatch(r"(?:after_tax_npv|cash|total_debt)_[a-z]{3}", parameter))
        or bool(re.fullmatch(r"annual_payable_[a-z]+_(?:ounces|pounds)", parameter))
        or bool(re.fullmatch(r"study_metal_price_[a-z]+_usd_per_(?:ounce|pound)", parameter))
    )


def metric_explanation(label: str) -> str:
    metric_name = label.split(" (", 1)[0].replace("AuEq", "AgEq")
    return METRIC_EXPLANATIONS.get(metric_name, "Derived from the current stored model inputs.")


def equivalent_metal_label(primary_commodity: str) -> str:
    return "AuEq" if primary_commodity.lower() == "gold" else "AgEq"


def configure_dialog(dialog: QDialog) -> None:
    palette = dialog.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#1c2822"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#1c2822"))
    dialog.setPalette(palette)
    dialog.setAutoFillBackground(True)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    parent = dialog.parentWidget()
    if parent is not None:
        dialog.finished.connect(
            lambda _: QTimer.singleShot(0, lambda: (parent.raise_(), parent.activateWindow(), parent.setFocus()))
        )


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
        self.inputs: dict[str, QComboBox | QDoubleSpinBox] = {}
        self.setWindowTitle("Settings")

        form = QFormLayout(self)
        for definition in APPLICATION_SETTINGS:
            value = database.get_current_application_setting(definition.key)
            if definition.choices:
                setting_input = QComboBox()
                setting_input.addItems(definition.choices)
                setting_input.setCurrentText(
                    value.value if value is not None else definition.default_value
                )
            else:
                setting_input = QDoubleSpinBox()
                setting_input.setRange(definition.minimum or 0, definition.maximum or 1_000_000)
                setting_input.setDecimals(0)
                setting_input.setSingleStep(definition.step or 1)
                setting_input.setPrefix("$")
                setting_input.setSuffix("/oz")
                setting_input.setValue(float(value.value if value is not None else definition.default_value))
            setting_input.setObjectName(definition.key)
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
            setting_input = self.inputs[definition.key]
            value = (
                setting_input.currentText()
                if isinstance(setting_input, QComboBox)
                else f"{setting_input.value():.0f}"
            )
            current = self.database.get_current_application_setting(definition.key)
            if current is None or current.value != value:
                self.database.set_application_setting(definition.key, value)
        super().accept()


class MetricExplanationDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        configure_dialog(self)
        self.setWindowTitle("Metric explanations")
        self.resize(840, 760)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 24)
        content_layout.setSpacing(14)

        notation_heading = QLabel("Variables")
        notation_heading.setObjectName("notation-heading")
        content_layout.addWidget(notation_heading)
        introduction = QLabel(
            "The equations below use the following symbols. Values are illustrative "
            "VZLA-style examples and should be read with the sourcing notes in Analysis."
        )
        introduction.setObjectName("notation-text")
        introduction.setWordWrap(True)
        content_layout.addWidget(introduction)
        for symbol, name, explanation in VARIABLE_GUIDES:
            variable_label = QLabel(f"<b>{symbol} - {name}</b><br/>{explanation}")
            variable_label.setObjectName("variable-guide")
            variable_label.setWordWrap(True)
            variable_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            content_layout.addWidget(variable_label)

        for index, (metric, (formula, example)) in enumerate(METRIC_GUIDES.items(), 1):
            guide = QWidget()
            guide_layout = QVBoxLayout(guide)
            guide_layout.setContentsMargins(10, 6, 10, 6)
            guide_layout.setSpacing(8)

            heading = QLabel(f"{index}. {metric}")
            heading.setObjectName("metric-guide-title")
            guide_layout.addWidget(heading)
            purpose_label = QLabel(METRIC_PURPOSES[metric])
            purpose_label.setObjectName("metric-purpose")
            purpose_label.setWordWrap(True)
            purpose_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            guide_layout.addWidget(purpose_label)

            formula_label = QLabel()
            formula_label.setObjectName("math-formula")
            formula_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            formula_label.setPixmap(render_math_formula(formula))
            formula_label.setToolTip(formula)
            guide_layout.addWidget(formula_label)

            example_label = QLabel()
            example_label.setObjectName("math-example")
            example_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            example_label.setPixmap(render_math_formula(example))
            example_label.setToolTip(example)
            guide_layout.addWidget(example_label)
            variable_label = QLabel(f"Where {METRIC_VARIABLES[metric]}")
            variable_label.setObjectName("metric-variables")
            variable_label.setWordWrap(True)
            variable_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            guide_layout.addWidget(variable_label)
            content_layout.addWidget(guide)
        content_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content)
        close_button = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll_area)
        layout.addWidget(close_button)


class MinerDashboard(QWidget):
    def __init__(self, database: Database, miner: Miner) -> None:
        super().__init__()
        self.database = database
        self.miner = miner
        self.inputs_visible = False
        self.scenario_prices: dict[str, float] = {}
        self.development_risk_factor = 0.70
        self.additional_dilution_shares = 0.0
        self.include_potential_dilution = False
        self.include_potential_conversion = False
        self.active_tab = 1
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
        history_button = QPushButton("Review dossier history")
        history_button.clicked.connect(self.review_history)
        actions.addWidget(history_button)
        actions.addStretch()
        self.root_layout.addLayout(actions)

        tabs = QTabWidget()
        self.root_layout.addWidget(tabs, 1)
        overview_tab = QWidget()
        analysis_tab = QWidget()
        tabs.addTab(overview_tab, "Overview")
        tabs.addTab(analysis_tab, "Analysis")
        overview_layout = QVBoxLayout(overview_tab)
        analysis_layout = QVBoxLayout(analysis_tab)
        for layout in (
            overview_layout,
            analysis_layout,
        ):
            layout.setContentsMargins(16, 16, 16, 16)
            layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout = overview_layout

        parameters = self.database.list_current_parameters(self.miner.id)
        parameters, project_model = self._consolidated_project_model_parameters(parameters)
        has_partial_project_npv = project_model is not None and any(
            "after_tax_npv_usd" not in project for project in project_model.projects
        )
        has_partial_project_resource = project_model is not None and any(
            "total_resource_equivalent_ounces" not in project
            for project in project_model.projects
        )
        statuses = self.database.list_lifecycle_status_history(self.miner.id)
        if statuses:
            status = statuses[0]
            lifecycle_heading = QLabel("Lifecycle status")
            lifecycle_heading.setObjectName("section-heading")
            self.layout.addWidget(lifecycle_heading)
            status_detail = QLabel(status.status)
            status_detail.setObjectName("status-value")
            self.layout.addWidget(status_detail)
            update_status_button = QPushButton("Update lifecycle status")
            update_status_button.clicked.connect(lambda: self.update_lifecycle_status(status.status))
            self.layout.addWidget(update_status_button, alignment=Qt.AlignmentFlag.AlignLeft)

        overview_heading = QLabel("Sourced baseline")
        overview_heading.setObjectName("section-heading")
        self.layout.addWidget(overview_heading)
        if project_model is not None:
            project_model_detail = QLabel(
                f"Consolidated project model: {project_model.name}\n"
                f"As of {project_model.as_of_date} | {project_model.source}"
            )
            project_model_detail.setObjectName("analysis-note")
            project_model_detail.setWordWrap(True)
            self.layout.addWidget(project_model_detail)
        overview_form = QFormLayout()
        overview_parameters = [
            parameter
            for parameter in parameters
            if parameter.parameter != "potential_conversion_shares"
        ]
        for parameter in overview_parameters:
            name = parameter.parameter.replace("_", " ").title()
            overview_form.addRow(name, QLabel(f"{parameter.value:,.12g} {parameter.unit}"))
        self.layout.addLayout(overview_form)

        sources = []
        if statuses:
            sources.append(("Lifecycle status", status.as_of_date, status.source))
        sources.extend(
            (parameter.parameter.replace("_", " ").title(), parameter.as_of_date, parameter.source)
            for parameter in overview_parameters
        )
        grouped_sources: dict[tuple[str, str], list[str]] = {}
        for label, as_of_date, source in sources:
            grouped_sources.setdefault((as_of_date, source), []).append(label)
        if grouped_sources:
            sources_heading = QLabel("Sources")
            sources_heading.setObjectName("section-heading")
            self.layout.addWidget(sources_heading)
            for (as_of_date, source), labels in grouped_sources.items():
                source_detail = QLabel(
                    f"{', '.join(labels)}\nAs of {as_of_date} | {source}"
                )
                source_detail.setObjectName("analysis-note")
                source_detail.setWordWrap(True)
                self.layout.addWidget(source_detail)

        market_snapshot = self.database.get_latest_market_snapshot(self.miner.id)
        trading_currency = self.miner.trading_currency
        usd_to_trading_rate = self._usd_to_currency_rate(trading_currency)
        self.layout = analysis_layout
        analysis_heading = QLabel("Current analysis")
        analysis_heading.setObjectName("section-heading")
        self.layout.addWidget(analysis_heading)
        explain_metrics_button = QPushButton("Explain metrics")
        explain_metrics_button.setObjectName("explain-metrics")
        explain_metrics_button.clicked.connect(self.show_metric_explanations)
        self.layout.addWidget(explain_metrics_button, alignment=Qt.AlignmentFlag.AlignLeft)
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
            equivalent_label = equivalent_metal_label(self.miner.primary_commodity)
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
                (f"{equivalent_label} price ($/{equivalent_label} oz)", self._format_currency_value(analysis.equivalent_price_usd_per_ounce, "USD", "‡")),
                (f"Margin per {equivalent_label} oz ($)", self._format_currency_value(analysis.margin_usd_per_equivalent_ounce, "USD")),
                (f"Annual {equivalent_label} oz / share (oz)", f"{analysis.annual_equivalent_ounces_per_share:,.4f}{production_marker}"),
                (f"Lifetime {equivalent_label} oz / share (oz)", f"{analysis.lifetime_equivalent_ounces_per_share:,.4f}{lifetime_marker}"),
            ):
                metric = QWidget()
                metric.setFixedWidth(METRIC_WIDTH)
                metric_layout = QVBoxLayout(metric)
                metric_layout.setContentsMargins(0, 0, 16, 8)
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
                    f"{'Partial ' if has_partial_project_npv else ''}Risked NAV / share ({self._currency_symbol(trading_currency)})",
                    "Unavailable"
                    if analysis.risked_nav_usd_per_share is None
                    else self._format_currency_value(
                        analysis.risked_nav_usd_per_share * usd_to_trading_rate,
                        trading_currency,
                        "*",
                    ),
                ),
                (
                    f"{'Partial ' if has_partial_project_npv else ''}Risked NAV / SP (x)",
                    "Unavailable"
                    if analysis.risked_nav_to_price is None
                    else self._format_ratio(analysis.risked_nav_to_price, "*"),
                ),
                (
                    f"{'Partial ' if has_partial_project_npv else ''}NAV / share ({self._currency_symbol(trading_currency)})",
                    "Unavailable"
                    if analysis.equity_nav_usd_per_share is None
                    else self._format_currency_value(
                        analysis.equity_nav_usd_per_share * usd_to_trading_rate,
                        trading_currency,
                        "*",
                    ),
                ),
                (
                    f"{'Partial ' if has_partial_project_npv else ''}NAV / SP (x)",
                    "Unavailable"
                    if analysis.equity_nav_to_price is None
                    else self._format_ratio(analysis.equity_nav_to_price, "*"),
                ),
            ]
            if analysis.npv_usd_per_share is not None:
                detailed_metrics.extend(
                    [
                        (f"{'Partial ' if has_partial_project_npv else ''}After-tax NPV / share ({self._currency_symbol(trading_currency)})", self._format_currency_value(analysis.npv_usd_per_share * usd_to_trading_rate, trading_currency, "*")),
                        (f"{'Partial ' if has_partial_project_npv else ''}NPV / SP (x)", self._format_ratio(analysis.npv_to_price, "*")),
                    ]
                )
            detailed_metrics.append(
                (
                    f"Lifetime margin / share ({self._currency_symbol(trading_currency)})",
                    self._format_currency_value(
                        analysis.lifetime_margin_usd_per_share * usd_to_trading_rate,
                        trading_currency,
                    ),
                )
            )
            results = QHBoxLayout()
            for index, (label, value) in enumerate(detailed_metrics):
                metric = QWidget()
                metric_layout = QVBoxLayout(metric)
                metric_layout.setContentsMargins(0, 8, 16, 8)
                metric_label = QLabel(label)
                metric_label.setObjectName("metric-label")
                metric_label.setToolTip(metric_explanation(label))
                metric_value = self._metric_value_widget(
                    value, metric_explanation(label)
                )
                metric_layout.addWidget(metric_label)
                metric_layout.addWidget(metric_value)
                metric.setFixedWidth(METRIC_WIDTH)
                results.addWidget(metric)
            results.addStretch()
            self.layout.addLayout(results)
            aisc_snapshot = parameter_snapshots.get("aisc_per_ounce")
            if aisc_snapshot is not None:
                aisc_row = QHBoxLayout()
                aisc_metric = QWidget()
                aisc_metric.setFixedWidth(METRIC_WIDTH)
                aisc_layout = QVBoxLayout(aisc_metric)
                aisc_layout.setContentsMargins(0, 8, 16, 8)
                aisc_label = QLabel(f"AISC ($/{equivalent_label} oz)")
                aisc_label.setObjectName("metric-label")
                aisc_label.setToolTip(metric_explanation("AISC"))
                aisc_value = self._metric_value_widget(
                    self._format_currency_value(aisc_snapshot.value, "USD", "†"),
                    metric_explanation("AISC"),
                )
                aisc_layout.addWidget(aisc_label)
                aisc_layout.addWidget(aisc_value)
                aisc_row.addWidget(aisc_metric)
                if mine_life_snapshot is not None:
                    mine_life_metric = QWidget()
                    mine_life_metric.setFixedWidth(METRIC_WIDTH)
                    mine_life_layout = QVBoxLayout(mine_life_metric)
                    mine_life_layout.setContentsMargins(0, 8, 16, 8)
                    mine_life_label = QLabel("Mine life (years)")
                    mine_life_label.setObjectName("metric-label")
                    mine_life_label.setToolTip(metric_explanation("Mine life"))
                    mine_life_value = self._metric_value_widget(
                        f"{mine_life_snapshot.value:,.2f}¶",
                        metric_explanation("Mine life"),
                    )
                    mine_life_layout.addWidget(mine_life_label)
                    mine_life_layout.addWidget(mine_life_value)
                    aisc_row.addWidget(mine_life_metric)
                aisc_row.addStretch()
                self.layout.addLayout(aisc_row)
            lifetime_margin_metric = QWidget()
            lifetime_margin_metric.setFixedWidth(METRIC_WIDTH)
            lifetime_margin_layout = QVBoxLayout(lifetime_margin_metric)
            lifetime_margin_layout.setContentsMargins(0, 8, 16, 8)
            lifetime_margin_label = QLabel("Lifetime margin / SP (x)")
            lifetime_margin_label.setObjectName("metric-label")
            lifetime_margin_label.setToolTip(metric_explanation("Lifetime margin / SP"))
            lifetime_margin_value = self._metric_value_widget(
                self._format_ratio(analysis.lifetime_margin_to_price),
                metric_explanation("Lifetime margin / SP"),
            )
            lifetime_margin_layout.addWidget(lifetime_margin_label)
            lifetime_margin_layout.addWidget(lifetime_margin_value)

            resource_snapshot = parameter_snapshots.get("total_resource_equivalent_ounces")
            if analysis.resource_equivalent_ounces_per_share is not None:
                resource_row = QHBoxLayout()
                for label, value in (
                    (
                        f"{'Partial ' if has_partial_project_resource else ''}Resource {equivalent_label} oz / share (oz)",
                        f"{analysis.resource_equivalent_ounces_per_share:,.4f}#",
                    ),
                    (
                        f"{'Partial ' if has_partial_project_resource else ''}Resource margin / SP (x)",
                        self._format_ratio(analysis.resource_margin_to_price, "#"),
                    ),
                ):
                    metric = QWidget()
                    metric.setFixedWidth(METRIC_WIDTH)
                    metric_layout = QVBoxLayout(metric)
                    metric_layout.setContentsMargins(0, 8, 16, 8)
                    metric_label = QLabel(label)
                    metric_label.setObjectName("metric-label")
                    metric_label.setToolTip(metric_explanation(label))
                    metric_value = self._metric_value_widget(
                        value, metric_explanation(label)
                    )
                    metric_layout.addWidget(metric_label)
                    metric_layout.addWidget(metric_value)
                    resource_row.addWidget(metric)
                resource_row.addWidget(lifetime_margin_metric)
                resource_row.addStretch()
                self.layout.addLayout(resource_row)
            else:
                lifetime_margin_row = QHBoxLayout()
                lifetime_margin_row.addWidget(lifetime_margin_metric)
                lifetime_margin_row.addStretch()
                self.layout.addLayout(lifetime_margin_row)
            self._render_scenario_analysis(
                parameters, market_snapshot, analysis, trading_currency, usd_to_trading_rate
            )
            self._render_dilution_analysis(
                analysis,
                trading_currency,
                usd_to_trading_rate,
                parameter_values.get("potential_dilution_shares"),
                parameter_values.get("potential_conversion_shares"),
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
            if mine_life_snapshot is not None:
                mine_life_note = QLabel(
                    f"¶ Mine life source: {mine_life_snapshot.source} "
                    f"| As of {mine_life_snapshot.as_of_date}."
                )
                mine_life_note.setObjectName("analysis-note")
                mine_life_note.setWordWrap(True)
                self.layout.addWidget(mine_life_note)
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
                if (
                    match := re.fullmatch(
                        r"annual_payable_([a-z]+)_(?:ounces|pounds)", parameter
                    )
                )
                and (snapshot := self.database.get_latest_commodity_price(match.group(1)))
            ]
            if metal_price_snapshots:
                prices_text = ", ".join(
                    f"{snapshot.commodity.title()} "
                    f"{self._format_currency_value(snapshot.price, snapshot.currency)}"
                    f"/{snapshot.unit.rsplit('/', 1)[-1]}"
                    for snapshot in sorted(
                        metal_price_snapshots,
                        key=lambda snapshot: (
                            snapshot.commodity != self.miner.primary_commodity.lower(),
                            snapshot.commodity,
                        ),
                    )
                )
                metal_price_note = QLabel(f"‡ {equivalent_label} metal prices: {prices_text}.")
                metal_price_note.setObjectName("analysis-note")
                metal_price_note.setWordWrap(True)
                self.layout.addWidget(metal_price_note)
            if annual_production_snapshot is not None and shares_snapshot is not None:
                production_note = QLabel(
                    f"§ Annual {equivalent_label} oz / share sources: "
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
                    f"¶ Lifetime {equivalent_label} oz / share sources: "
                    f"production: {annual_production_snapshot.source} "
                    f"| As of {annual_production_snapshot.as_of_date}; "
                    f"mine life: {mine_life_snapshot.source} "
                    f"| As of {mine_life_snapshot.as_of_date}."
                )
                lifetime_note.setObjectName("analysis-note")
                lifetime_note.setWordWrap(True)
                self.layout.addWidget(lifetime_note)

        for label in self.findChildren(QLabel):
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
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
        metal_volumes = self._payable_metal_volumes(values)
        if metal_volumes is None:
            return None
        if metal_prices is None:
            metal_prices = {}
            for metal in metal_volumes:
                price = self.database.get_latest_commodity_price(metal)
                if (
                    price is None
                    or price.currency != "USD"
                    or price.unit != COMMODITIES[metal].price_unit
                ):
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
                shares_outstanding=(
                    values["basic_shares_outstanding"]
                    + (
                        values.get("potential_dilution_shares", 0)
                        if self.include_potential_dilution
                        else 0
                    )
                    + (
                        values.get("potential_conversion_shares", 0)
                        if self.include_potential_conversion
                        else 0
                    )
                ),
                share_price_usd=quote_price_usd,
                total_resource_equivalent_ounces=values.get("total_resource_equivalent_ounces"),
                after_tax_npv_usd=values.get("after_tax_npv_usd"),
                cash_usd=self._financial_value_usd(values, "cash"),
                total_debt_usd=self._financial_value_usd(values, "total_debt"),
                development_risk_factor=self.development_risk_factor,
                additional_dilution_shares=self.additional_dilution_shares,
                potential_conversion_shares=(
                    None
                    if self.include_potential_conversion
                    else values.get("potential_conversion_shares")
                ),
            )
        )

    def _consolidated_project_model_parameters(self, parameters):
        project_model = self.database.get_latest_project_model_snapshot(self.miner.id)
        if project_model is None:
            return parameters, None
        try:
            projects = [
                ProjectInputs(
                    name=str(project["name"]),
                    annual_payable_metal_volumes={
                        str(metal): float(volume)
                        for metal, volume in dict(project["annual_payable_metal_volumes"]).items()
                    },
                    annual_equivalent_ounces=float(project["annual_equivalent_ounces"]),
                    aisc_usd_per_equivalent_ounce=float(
                        project["aisc_usd_per_equivalent_ounce"]
                    ),
                    mine_life_years=float(project["mine_life_years"]),
                    total_resource_equivalent_ounces=(
                        float(project["total_resource_equivalent_ounces"])
                        if project.get("total_resource_equivalent_ounces") is not None
                        else None
                    ),
                    after_tax_npv_usd=(
                        float(project["after_tax_npv_usd"])
                        if project.get("after_tax_npv_usd") is not None
                        else None
                    ),
                )
                for project in project_model.projects
            ]
            consolidated = consolidate_project_inputs(projects)
        except (KeyError, TypeError, ValueError):
            return parameters, None
        source = f"Consolidated project model '{project_model.name}': {project_model.source}"
        snapshots = {snapshot.parameter: snapshot for snapshot in parameters}
        for parameter in tuple(snapshots):
            if re.fullmatch(r"annual_payable_[a-z]+_(?:ounces|pounds)", parameter):
                del snapshots[parameter]
        values = {
            "annual_production_ounces": (consolidated.annual_equivalent_ounces, "AgEq oz/year"),
            "aisc_per_ounce": (consolidated.aisc_usd_per_equivalent_ounce, "USD/AgEq oz"),
            "mine_life_years": (consolidated.mine_life_years, "years"),
        }
        resource_value = (
            consolidated.total_resource_equivalent_ounces
            or consolidated.partial_total_resource_equivalent_ounces
        )
        if resource_value is not None:
            values["total_resource_equivalent_ounces"] = (
                resource_value,
                "AgEq oz",
            )
        npv_value = consolidated.after_tax_npv_usd or consolidated.partial_after_tax_npv_usd
        if npv_value is not None:
            values["after_tax_npv_usd"] = (npv_value, "USD")
        for metal, volume in consolidated.annual_payable_metal_volumes.items():
            values[f"annual_payable_{metal}_ounces"] = (volume, f"{metal.title()} oz/year")
        for parameter, (value, unit) in values.items():
            snapshots[parameter] = ParameterSnapshot(
                0, self.miner.id, parameter, value, unit, project_model.as_of_date, source
            )
        return list(snapshots.values()), project_model

    def _financial_value_usd(self, values: dict[str, float], parameter: str) -> float | None:
        usd_value = values.get(f"{parameter}_usd")
        if usd_value is not None:
            return usd_value
        prefix = f"{parameter}_"
        for name, value in values.items():
            if not name.startswith(prefix):
                continue
            currency = name.removeprefix(prefix).upper()
            rate = self._usd_to_currency_rate(currency)
            if rate is not None:
                return value / rate
        return None

    def _current_metal_prices(self, parameters) -> dict[str, float] | None:
        values = {parameter.parameter: parameter.value for parameter in parameters}
        metals = self._payable_metal_volumes(values)
        if metals is None:
            return None
        prices = {}
        for metal in metals:
            price = self.database.get_latest_commodity_price(metal)
            if (
                price is None
                or price.currency != "USD"
                or price.unit != COMMODITIES[metal].price_unit
            ):
                return None
            prices[metal] = price.price
        return prices

    def _payable_metal_volumes(self, values: dict[str, float]) -> dict[str, float] | None:
        volumes = {}
        for parameter, value in values.items():
            match = re.fullmatch(r"annual_payable_([a-z]+)_(ounces|pounds)", parameter)
            if match is None:
                continue
            metal, quantity = match.groups()
            definition = COMMODITIES.get(metal)
            if definition is None or definition.volume_unit_suffix != quantity:
                return None
            volumes[metal] = value
        return volumes

    def _render_scenario_analysis(
        self, parameters, market_snapshot, current, trading_currency: str, usd_to_trading_rate: float
    ) -> None:
        equivalent_label = equivalent_metal_label(self.miner.primary_commodity)
        current_prices = self._current_metal_prices(parameters)
        if current_prices is None:
            return
        for metal, price in current_prices.items():
            self.scenario_prices.setdefault(metal, self._scenario_default_price(metal, price))

        self.layout.addWidget(QLabel("Scenario metal prices"))
        controls = QFormLayout()
        for metal in sorted(current_prices):
            definition = COMMODITIES[metal]
            price_input = QDoubleSpinBox()
            price_input.setObjectName(f"scenario-price-{metal}")
            price_input.setRange(0.01, max(current_prices[metal] * 3, 10_000))
            price_input.setDecimals(definition.scenario_decimals)
            price_input.setSingleStep(definition.scenario_step)
            price_input.setPrefix("$")
            price_input.setSuffix(f"/{definition.price_unit.rsplit('/', 1)[-1]}")
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
                    commodity, self._scenario_default_price(commodity, price)
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
            (f"Future {equivalent_label} price ($/{equivalent_label} oz)", self._format_currency_value(scenario.equivalent_price_usd_per_ounce, "USD")),
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
            metric_layout.setContentsMargins(0, 0, 16, 8)
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

    def _scenario_default_price(self, commodity: str, market_price: float) -> float:
        definition = {
            "gold": DEFAULT_SCENARIO_GOLD_PRICE,
            "silver": DEFAULT_SCENARIO_SILVER_PRICE,
        }.get(commodity)
        if definition is None:
            return market_price
        setting = self.database.get_current_application_setting(definition.key)
        return float(setting.value if setting is not None else definition.default_value)

    def set_development_risk_factor(self, risk_factor: float) -> None:
        self.development_risk_factor = risk_factor
        self.render()

    def _render_dilution_analysis(
        self,
        analysis,
        trading_currency: str,
        usd_to_trading_rate: float,
        potential_dilution_shares: float | None,
        potential_conversion_shares: float | None,
    ) -> None:
        if analysis.diluted_equity_nav_usd_per_share is None:
            return
        self.layout.addWidget(QLabel("Dilution scenario"))
        if potential_dilution_shares is not None:
            include_dilution = QCheckBox(
                f"Include documented dilution ({potential_dilution_shares:,.0f} shares)"
            )
            include_dilution.setObjectName("include-potential-dilution")
            include_dilution.setChecked(self.include_potential_dilution)
            include_dilution.setToolTip(
                "Use documented options, warrants, and RSUs in all per-share analysis metrics."
            )
            include_dilution.toggled.connect(self.set_include_potential_dilution)
            self.layout.addWidget(include_dilution)
        if potential_conversion_shares is not None:
            include_conversion = QCheckBox(
                f"Include potential conversion ({potential_conversion_shares:,.0f} shares)"
            )
            include_conversion.setObjectName("include-potential-conversion")
            include_conversion.setChecked(self.include_potential_conversion)
            include_conversion.setToolTip(
                "Use potential conversion shares in all per-share metrics. Debt treatment remains unchanged."
            )
            include_conversion.toggled.connect(self.set_include_potential_conversion)
            self.layout.addWidget(include_conversion)
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

    def set_include_potential_dilution(self, include: bool) -> None:
        self.include_potential_dilution = include
        self.render()

    def set_include_potential_conversion(self, include: bool) -> None:
        self.include_potential_conversion = include
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

    def show_metric_explanations(self) -> None:
        MetricExplanationDialog(self).exec()

    def add_milestone(self) -> None:
        dialog = AddMilestoneDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.database.add_milestone(self.miner.id, *dialog.values())
            self.render()


class MainWindow(QMainWindow):
    WINDOW_GEOMETRY_SETTING = "window_geometry"

    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database
        self.setWindowTitle("Gosimine")
        self._restore_window_geometry()
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

    def _restore_window_geometry(self) -> None:
        setting = self.database.get_current_application_setting(self.WINDOW_GEOMETRY_SETTING)
        if setting is None:
            self.resize(1600, 1000)
            return
        try:
            geometry = json.loads(setting.value)
            self.setGeometry(
                int(geometry["x"]),
                int(geometry["y"]),
                int(geometry["width"]),
                int(geometry["height"]),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            self.resize(1600, 1000)

    def closeEvent(self, event) -> None:
        geometry = self.normalGeometry()
        self.database.set_application_setting(
            self.WINDOW_GEOMETRY_SETTING,
            json.dumps(
                {
                    "x": geometry.x(),
                    "y": geometry.y(),
                    "width": geometry.width(),
                    "height": geometry.height(),
                }
            ),
            "Application",
        )
        super().closeEvent(event)

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
            apply_application_style(self.database)
            if isinstance(self.detail, MinerDashboard):
                self.detail.render()


def main() -> None:
    application = QApplication(sys.argv)
    database_path = Path("data") / "gosimine.sqlite3"
    initialize_database(database_path, Path("seed") / "miners")
    database = Database(database_path)
    apply_application_style(database)
    window = MainWindow(database)
    window.show()
    exit_code = application.exec()
    database.close()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()

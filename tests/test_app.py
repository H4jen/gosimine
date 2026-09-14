import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QLabel,
    QPushButton,
    QTableWidget,
    QTabWidget,
)

from gosimine.app import (
    HistoryDialog,
    MainWindow,
    MetricExplanationDialog,
    MinerDashboard,
    SettingsDialog,
)
from gosimine.database import Database
from gosimine.seed import initialize_database


def select_seeded_vzla(database: Database):
    return database.select_catalog_miner("VZLA")


def test_main_window_selects_a_catalog_miner(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners"
    initialize_database(database_path, seed_path)
    database = Database(database_path)

    class AcceptedCatalogDialog:
        selected_ticker = "VZLA"

        def __init__(self, supplied_database, parent) -> None:
            assert supplied_database is database

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr("gosimine.app.CatalogDialog", AcceptedCatalogDialog)
    application = QApplication.instance() or QApplication([])
    window = MainWindow(database)
    window.select_catalog_miner()
    application.processEvents()

    assert database.get_miner_by_ticker("VZLA") is not None
    assert window.table.rowCount() == 1
    assert window.table.columnCount() == 1
    assert window.table.item(0, 0).text() == "VZLA: Vizsla Silver"
    assert window.table.verticalHeader().isHidden()
    window.close()
    database.close()


def test_main_window_shows_dashboard_when_a_miner_is_selected(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")
    application = QApplication.instance() or QApplication([])
    window = MainWindow(database)
    window.show()
    application.processEvents()

    assert isinstance(window.detail, MinerDashboard)
    assert window.table.currentRow() == 0
    assert window.width() == 1600
    assert window.height() == 1000
    detail_pane = window.splitter.widget(1)
    assert detail_pane is window.detail_scroll
    assert detail_pane.minimumWidth() == 480
    assert window.table.maximumWidth() == 240
    window.close()
    database.close()


def test_main_window_restores_its_previous_size(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    application = QApplication.instance() or QApplication([])
    window = MainWindow(database)
    window.resize(1500, 950)
    window.close()

    restored_window = MainWindow(database)
    restored_window.show()
    application.processEvents()

    assert restored_window.width() == 1500
    assert restored_window.height() == 950
    restored_window.close()
    database.close()


def test_miner_dashboard_displays_seeded_vzla_data(tmp_path: Path) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners"
    initialize_database(database_path, seed_path)
    database = Database(database_path)
    miner = select_seeded_vzla(database)
    database.add_market_snapshot(
        miner.id,
        4.10,
        "USD",
        "2026-09-12T20:00:00+00:00",
        "2026-09-12T21:00:00+00:00",
        "Yahoo Finance",
    )
    database.add_parameter_snapshot(
        miner.id,
        "basic_shares_outstanding",
        355_056_872,
        "shares",
        "2026-09-12",
        "Yahoo Finance",
    )
    database.add_parameter_snapshot(
        miner.id,
        "potential_dilution_shares",
        20_000_000,
        "shares",
        "2026-09-12",
        "Issuer filing",
    )
    database.add_commodity_price_snapshot(
        "silver",
        64.55,
        "USD",
        "USD/oz",
        "2026-09-12T20:00:00+00:00",
        "2026-09-12T21:00:00+00:00",
        "Yahoo Finance",
    )
    database.add_commodity_price_snapshot(
        "gold",
        4_366.20,
        "USD",
        "USD/oz",
        "2026-09-12T20:00:00+00:00",
        "2026-09-12T21:00:00+00:00",
        "Yahoo Finance",
    )
    database.add_exchange_rate_snapshot(
        "USD", "SEK", 10.45, "2026-09-12T21:00:00+00:00", "Yahoo Finance"
    )

    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    dashboard.show()
    application.processEvents()
    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))

    assert "Vizsla Silver" in text
    assert "VZLA" in text
    assert "Developer / permitting" in text
    assert "4.10" in text
    assert "Share price ($)" in text
    assert "AgEq price ($/AgEq oz)" in text
    assert "AISC ($/AgEq oz)" in text
    assert "10.61 $" in text
    assert "58.46 $" in text
    assert "0.0490" in text
    assert "0.4602" in text
    assert "1.0170" in text
    assert "Annual margin / share" in text
    assert "Lifetime margin / SP" in text
    assert "Resource AgEq oz / share" in text
    assert "Resource margin / SP" in text
    assert "NPV / SP" in text
    npv_label = next(
        label
        for label in dashboard.findChildren(QLabel)
        if label.text() == "After-tax NPV / share ($)"
    )
    assert "feasibility-study NPV" in npv_label.toolTip()
    assert "5.08 $" in text
    assert "3.88 $" in text
    assert "5.54 $" in text
    assert "0.95x" in text
    assert "1.35x" in text
    assert "1.24x" in text
    assert [
        label.text()
        for label in dashboard.findChildren(QLabel)
        if label.objectName() == "metric-marker"
    ] == ["‡", "§", "§", "*", "*", "*", "*", "*", "*", "†", "¶", "#", "#", "#"]
    assert "* Silver $35.50/oz, Gold $3,100.00/oz; 5% discount rate; FS: https://vizslasilvercorp.com/" in text
    assert "† AISC source: https://vizslasilvercorp.com/" in text
    assert "# Resource screening uses total measured, indicated, and inferred in-situ resources" in text
    assert "‡ AgEq metal prices: Silver 64.55 $/oz, Gold 4,366.20 $/oz." in text
    assert "§ Annual AgEq oz / share sources: production: https://vizslasilvercorp.com/" in text
    assert "As of 2025-11-12." in text
    assert "NAV / share" in text
    assert "Future case" in text
    assert "Future annual margin / share" in text
    tabs = dashboard.findChild(QTabWidget)
    assert tabs is not None
    assert tabs.currentIndex() == 1
    assert all(
        label.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse
        for label in dashboard.findChildren(QLabel)
    )
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Overview",
        "Analysis",
    ]
    overview_text = "\n".join(
        label.text() for label in tabs.widget(0).findChildren(QLabel)
    )
    assert "Key milestones" not in overview_text
    assert "Sourced baseline" in overview_text
    assert "10,130,000 Ag oz/year" in overview_text
    assert "222,400,000 AgEq oz" in overview_text
    assert "138,700,000 AgEq oz" in overview_text
    assert "361,100,000 AgEq oz" in overview_text
    assert "406,495,000 USD" in overview_text
    assert "Potential Conversion Shares" not in overview_text
    assert "Sources" in overview_text
    assert "As of 2025-11-12 | https://vizslasilvercorp.com/" in overview_text
    assert any(
        button.text() == "Refresh market data"
        for button in dashboard.findChildren(QPushButton)
    )
    assert any(
        button.objectName() == "explain-metrics"
        for button in dashboard.findChildren(QPushButton)
    )
    dilution_checkbox = dashboard.findChild(QCheckBox, "include-potential-dilution")
    assert dilution_checkbox is not None
    assert not dilution_checkbox.isChecked()
    dilution_checkbox.setChecked(True)
    application.processEvents()
    diluted_text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "Shares after dilution\n375,056,872" in diluted_text
    conversion_checkbox = dashboard.findChild(QCheckBox, "include-potential-conversion")
    assert conversion_checkbox is not None
    assert not conversion_checkbox.isChecked()
    conversion_checkbox.setChecked(True)
    application.processEvents()
    converted_text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "Shares after dilution\n426,448,732" in converted_text
    assert any(
        button.text() == "Update lifecycle status"
        for button in dashboard.findChildren(QPushButton)
    )

    dashboard.close()
    database.close()


def test_miner_dashboard_displays_seeded_abra_data(tmp_path: Path) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners"
    initialize_database(database_path, seed_path)
    database = Database(database_path)
    miner = database.select_catalog_miner("ABRA.TO")
    database.add_market_snapshot(
        miner.id,
        13.70,
        "CAD",
        "2026-09-14T20:00:00+00:00",
        "2026-09-14T21:00:00+00:00",
        "Yahoo Finance",
    )
    for commodity, price in {"silver": 64.55, "gold": 4_366.20}.items():
        database.add_commodity_price_snapshot(
            commodity,
            price,
            "USD",
            "USD/oz",
            "2026-09-14T20:00:00+00:00",
            "2026-09-14T21:00:00+00:00",
            "Yahoo Finance",
        )
    database.add_exchange_rate_snapshot(
        "USD", "CAD", 1.40, "2026-09-14T21:00:00+00:00", "Yahoo Finance"
    )

    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    dashboard.show()
    application.processEvents()
    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))

    assert "Analysis unavailable until market and model inputs are refreshed." not in text
    assert "AgEq price ($/AgEq oz)" in text
    assert "NAV / share (C$)" in text
    assert "Lifetime margin / SP (x)" in text

    dashboard.close()
    database.close()


def test_miner_dashboard_recalculates_a_temporary_metal_price_scenario(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners"
    initialize_database(database_path, seed_path)
    database = Database(database_path)
    miner = select_seeded_vzla(database)
    database.add_market_snapshot(
        miner.id, 4.10, "USD", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Yahoo Finance"
    )
    database.add_parameter_snapshot(
        miner.id, "basic_shares_outstanding", 355_056_872, "shares", "2026-09-12", "Yahoo Finance"
    )
    for commodity, price in {"silver": 64.55, "gold": 4_366.20}.items():
        database.add_commodity_price_snapshot(
            commodity, price, "USD", "USD/oz", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Yahoo Finance"
        )
    database.add_exchange_rate_snapshot(
        "USD", "SEK", 10.45, "2026-09-12T21:00:00+00:00", "Yahoo Finance"
    )

    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    silver_input = dashboard.findChild(QDoubleSpinBox, "scenario-price-silver")
    gold_input = dashboard.findChild(QDoubleSpinBox, "scenario-price-gold")
    assert silver_input is not None
    assert gold_input is not None
    assert silver_input.decimals() == 0
    assert gold_input.decimals() == 0
    assert silver_input.singleStep() == 10.0
    assert gold_input.singleStep() == 100.0
    assert silver_input.value() == 80
    assert gold_input.value() == 6000
    silver_input.setValue(70)
    silver_input.editingFinished.emit()
    application.processEvents()

    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "Future case" in text
    assert "Future AgEq price ($/AgEq oz)" in text
    assert "Future resource margin / SP" in text
    reset_button = dashboard.findChild(QPushButton, "scenario-reset-silver")
    assert reset_button is not None
    reset_button.click()
    application.processEvents()
    assert dashboard.scenario_prices["silver"] == 80
    assert database.get_latest_commodity_price("silver").price == 64.55
    dashboard.close()
    database.close()

def test_miner_dashboard_includes_copper_in_the_payable_metal_mix(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Copper Silver", "CUSI", "Silver", "Producer")
    for parameter, value in {
        "annual_payable_silver_ounces": 1_000_000,
        "annual_payable_copper_pounds": 5_000_000,
        "annual_production_ounces": 1_500_000,
        "aisc_per_ounce": 20,
        "mine_life_years": 5,
        "basic_shares_outstanding": 100_000_000,
    }.items():
        database.add_parameter_snapshot(
            miner.id, parameter, value, "test", "2026-09-12", "Test"
        )
    database.add_market_snapshot(
        miner.id,
        5.00,
        "USD",
        "2026-09-12T20:00:00+00:00",
        "2026-09-12T21:00:00+00:00",
        "Test",
    )
    for commodity, price, unit in (
        ("silver", 30.00, "USD/oz"),
        ("copper", 4.50, "USD/lb"),
    ):
        database.add_commodity_price_snapshot(
            commodity,
            price,
            "USD",
            unit,
            "2026-09-12T20:00:00+00:00",
            "2026-09-12T21:00:00",
            "Test",
        )

    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    application.processEvents()

    copper_input = dashboard.findChild(QDoubleSpinBox, "scenario-price-copper")
    assert copper_input is not None
    assert copper_input.decimals() == 2
    assert copper_input.singleStep() == 0.25
    assert copper_input.suffix() == "/lb"
    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "Copper 4.50 $/lb" in text
    assert "Future case" in text

    dashboard.close()
    database.close()


def test_miner_dashboard_shows_lifetime_margin_to_price_without_resources(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Gold Producer", "GOLD", "Gold", "Producer")
    for parameter, value in {
        "annual_payable_gold_ounces": 100_000,
        "annual_production_ounces": 100_000,
        "aisc_per_ounce": 1_000,
        "mine_life_years": 5,
        "basic_shares_outstanding": 10_000_000,
    }.items():
        database.add_parameter_snapshot(
            miner.id, parameter, value, "test", "2026-09-14", "Test"
        )
    database.add_market_snapshot(
        miner.id, 10, "USD", "2026-09-14T20:00:00+00:00", "2026-09-14T21:00:00+00:00", "Test"
    )
    database.add_commodity_price_snapshot(
        "gold", 2_000, "USD", "USD/oz", "2026-09-14T20:00:00+00:00", "2026-09-14T21:00:00+00:00", "Test"
    )

    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    application.processEvents()

    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "Lifetime margin / SP (x)" in text
    assert "5.00x" in text
    dashboard.close()
    database.close()

def test_miner_dashboard_opens_metric_explanations(tmp_path: Path, monkeypatch) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")
    opened = False

    class MetricExplanationDialogStub:
        def __init__(self, parent) -> None:
            assert parent is dashboard

        def exec(self) -> QDialog.DialogCode:
            nonlocal opened
            opened = True
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr("gosimine.app.MetricExplanationDialog", MetricExplanationDialogStub)
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    explain_button = dashboard.findChild(QPushButton, "explain-metrics")

    assert explain_button is not None
    explain_button.click()
    application.processEvents()

    assert opened
    dashboard.close()
    database.close()


def test_metric_explanations_use_rich_text_math() -> None:
    application = QApplication.instance() or QApplication([])
    dialog = MetricExplanationDialog()
    formula_labels = dialog.findChildren(QLabel, "math-formula")
    example_labels = dialog.findChildren(QLabel, "math-example")
    variable_labels = dialog.findChildren(QLabel, "metric-variables")
    purpose_labels = dialog.findChildren(QLabel, "metric-purpose")
    notation = dialog.findChild(QLabel, "notation-text")
    variable_guide_labels = dialog.findChildren(QLabel, "variable-guide")

    assert formula_labels
    assert all(not label.pixmap().isNull() for label in formula_labels)
    assert any("\\frac" in label.toolTip() for label in formula_labels)
    assert all(label.pixmap().toImage().pixelColor(0, 0).alpha() == 0 for label in formula_labels)
    assert len(example_labels) == len(formula_labels)
    assert all(not label.pixmap().isNull() for label in example_labels)
    assert any("\\$58.47" in label.toolTip() for label in example_labels)
    assert all("USD" not in label.toolTip() for label in example_labels)
    assert any("6.77" in label.toolTip() for label in example_labels)
    assert len(variable_labels) == len(formula_labels)
    assert any("P_AgEq = equivalent-metal price" in label.text() for label in variable_labels)
    assert len(purpose_labels) == len(formula_labels)
    assert any("converts a mixed gold-and-silver production profile" in label.text() for label in purpose_labels)
    assert notation is not None
    assert "equations below" in notation.text()
    assert len(variable_guide_labels) == 19
    assert any("Share price" in label.text() for label in variable_guide_labels)

    dialog.close()
    application.processEvents()


def test_usd_listing_does_not_require_an_fx_rate(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners"
    initialize_database(database_path, seed_path)
    database = Database(database_path)
    miner = select_seeded_vzla(database)
    database.add_market_snapshot(
        miner.id, 4.10, "USD", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Yahoo Finance"
    )
    database.add_parameter_snapshot(
        miner.id, "basic_shares_outstanding", 355_056_872, "shares", "2026-09-12", "Yahoo Finance"
    )
    for commodity, price in {"silver": 64.55, "gold": 4_366.20}.items():
        database.add_commodity_price_snapshot(
            commodity, price, "USD", "USD/oz", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Yahoo Finance"
        )

    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))

    assert "Currency conversion unavailable" not in text
    assert "Future case" in text
    dashboard.close()
    database.close()


def test_miner_dashboard_converts_per_share_values_to_trading_currency(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA.TO", "Silver", "Developer", "CAD")
    database.add_market_snapshot(
        miner.id, 5.00, "CAD", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Yahoo Finance"
    )
    for parameter, value in {
        "annual_payable_silver_ounces": 10_130_000,
        "annual_payable_gold_ounces": 83_000,
        "annual_production_ounces": 17_383_000,
        "aisc_per_ounce": 10.61,
        "mine_life_years": 9.4,
        "basic_shares_outstanding": 355_056_872,
        "after_tax_npv_usd": 1_802_000_000,
        "cash_cad": 406_495_000,
        "total_debt_cad": 240_366_000,
    }.items():
        database.add_parameter_snapshot(
            miner.id, parameter, value, "test", "2026-09-12", "Test"
        )
    for commodity, price in {"silver": 64.55, "gold": 4_366.20}.items():
        database.add_commodity_price_snapshot(
            commodity, price, "USD", "USD/oz", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Test"
        )
    database.add_exchange_rate_snapshot("USD", "CAD", 1.36, "2026-09-12T21:00:00+00:00", "Test")

    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    application.processEvents()
    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))

    assert "5.00" in text
    assert "Share price (C$)" in text
    assert "3.19" in text
    assert "Annual margin / share (C$)" in text
    assert "Mine life (years)" in text
    assert "9.40" in text
    assert "NAV / share (C$)" in text
    assert "7.37 C$" in text
    dashboard.close()
    database.close()


def test_miner_dashboard_refresh_button_updates_market_data(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners"
    initialize_database(database_path, seed_path)
    database = Database(database_path)
    miner = select_seeded_vzla(database)

    def fake_refresh(database: Database, miner) -> None:
        database.add_market_snapshot(
            miner.id,
            4.10,
            "USD",
            "2026-09-12T20:00:00+00:00",
            "2026-09-12T21:00:00+00:00",
            "Yahoo Finance",
        )

    monkeypatch.setattr("gosimine.app.refresh_market_data", fake_refresh)
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    refresh_button = next(
        button
        for button in dashboard.findChildren(QPushButton)
        if button.text() == "Refresh market data"
    )

    refresh_button.click()
    application.processEvents()

    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "Analysis unavailable" in text
    snapshot = database.get_latest_market_snapshot(miner.id)
    assert snapshot is not None
    assert snapshot.price == 4.10
    dashboard.close()
    database.close()


def test_miner_dashboard_adds_research_note(tmp_path: Path, monkeypatch) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")

    class AcceptedResearchDialog:
        def __init__(self, parent) -> None:
            pass

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def values(self) -> tuple[str, str, str, str, str, str]:
            return (
                "2026-09-12",
                "Reviewed the feasibility study.",
                "https://example.com/vzla-fs",
                "No change.",
                "Permit decision.",
                "When is construction expected to start?",
            )

    monkeypatch.setattr("gosimine.app.AddResearchEntryDialog", AcceptedResearchDialog)
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)

    dashboard.add_research_note()
    application.processEvents()

    entries = database.list_research_entries(miner.id)
    assert len(entries) == 1
    assert entries[0].note == "Reviewed the feasibility study."
    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "Reviewed the feasibility study." not in text
    dashboard.close()
    database.close()


def test_miner_dashboard_adds_milestone(tmp_path: Path, monkeypatch) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")

    class AcceptedMilestoneDialog:
        def __init__(self, parent) -> None:
            pass

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def values(self) -> tuple[str, str, str, str, str, str]:
            return (
                "Permitting",
                "MIA permit decision",
                "2026-H2",
                "Planned",
                "Awaiting regulatory approval.",
                "Manual",
            )

    monkeypatch.setattr("gosimine.app.AddMilestoneDialog", AcceptedMilestoneDialog)
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)

    dashboard.add_milestone()
    application.processEvents()

    milestones = database.list_milestones(miner.id)
    assert len(milestones) == 1
    assert milestones[0].title == "MIA permit decision"
    dashboard.close()
    database.close()


def test_miner_dashboard_records_milestone_outcome(tmp_path: Path, monkeypatch) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")

    class AcceptedMilestoneOutcomeDialog:
        def __init__(self, category, title, parent) -> None:
            assert (category, title) == ("Permitting", "MIA permit decision")

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def values(self) -> tuple[str, str, str, str, str, str]:
            return (
                "Permitting",
                "MIA permit decision",
                "2026-09-12",
                "Completed",
                "Actual outcome: Permit received.\nThesis impact: De-risks construction.",
                "Company release",
            )

    monkeypatch.setattr("gosimine.app.UpdateMilestoneDialog", AcceptedMilestoneOutcomeDialog)
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    dashboard.update_milestone("Permitting", "MIA permit decision")
    application.processEvents()

    milestone = database.list_milestones(miner.id)[0]
    assert milestone.status == "Completed"
    assert "Thesis impact: De-risks construction." in milestone.detail
    dashboard.close()
    database.close()


def test_history_dialog_displays_prior_dossier_entries(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")
    database.add_parameter_snapshot(
        miner.id, "aisc_per_ounce", 11.0, "USD/AgEq oz", "2026-09-01", "Study"
    )
    database.add_lifecycle_status_snapshot(
        miner.id, "Developer / permitting", "2026-09-01", "Company release"
    )
    database.add_research_entry(
        miner.id, "2026-09-01", "Permit review underway.", "Company release", "", "", ""
    )
    application = QApplication.instance() or QApplication([])
    dialog = HistoryDialog(database, miner)
    application.processEvents()

    text = "\n".join(
        table.item(row, column).text()
        for table in dialog.findChildren(QTableWidget)
        for row in range(table.rowCount())
        for column in range(table.columnCount())
        if table.item(row, column) is not None
    )
    assert "aisc_per_ounce" in text
    assert "Developer / permitting" in text
    assert "Permit review underway." in text
    dialog.close()
    database.close()


def test_miner_dashboard_adds_a_model_input(tmp_path: Path, monkeypatch) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")

    class AcceptedModelInputDialog:
        def __init__(self, parent) -> None:
            pass

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def values(self) -> tuple[str, float, str, str, str]:
            return ("mine_life_years", 10.0, "years", "2026-09-12", "Manual")

    monkeypatch.setattr("gosimine.app.AddModelInputDialog", AcceptedModelInputDialog)
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)

    dashboard.add_model_input()
    application.processEvents()

    parameters = database.list_current_parameters(miner.id)
    assert len(parameters) == 1
    assert parameters[0].parameter == "mine_life_years"
    assert parameters[0].value == 10.0
    dashboard.close()
    database.close()


def test_miner_dashboard_updates_lifecycle_status(tmp_path: Path, monkeypatch) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")
    database.add_lifecycle_status_snapshot(
        miner.id, "Developer / permitting", "2026-09-01", "Company release"
    )

    class AcceptedLifecycleStatusDialog:
        def __init__(self, current_status, parent) -> None:
            assert current_status == "Developer / permitting"

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def values(self) -> tuple[str, str, str]:
            return ("Construction", "2026-09-12", "Company release")

    monkeypatch.setattr(
        "gosimine.app.UpdateLifecycleStatusDialog", AcceptedLifecycleStatusDialog
    )
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)

    dashboard.update_lifecycle_status("Developer / permitting")
    application.processEvents()

    statuses = database.list_lifecycle_status_history(miner.id)
    assert statuses[0].status == "Construction"
    text = "\n".join(label.text() for label in dashboard.findChildren(QLabel))
    assert "Construction" in text
    dashboard.close()
    database.close()


def test_miner_dashboard_saves_and_loads_a_scenario(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "gosimine.sqlite3"
    seed_path = Path(__file__).parents[1] / "seed" / "miners"
    initialize_database(database_path, seed_path)
    database = Database(database_path)
    miner = select_seeded_vzla(database)
    database.add_market_snapshot(
        miner.id, 4.10, "USD", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Test"
    )
    database.add_parameter_snapshot(
        miner.id, "basic_shares_outstanding", 355_056_872, "shares", "2026-09-12", "Test"
    )
    for commodity, price in {"silver": 64.55, "gold": 4_366.20}.items():
        database.add_commodity_price_snapshot(
            commodity, price, "USD", "USD/oz", "2026-09-12T20:00:00+00:00", "2026-09-12T21:00:00+00:00", "Test"
        )

    class AcceptedSaveScenarioDialog:
        def __init__(self, parent) -> None:
            pass

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted

        def value(self) -> str:
            return "Higher silver"

    monkeypatch.setattr("gosimine.app.SaveScenarioDialog", AcceptedSaveScenarioDialog)
    application = QApplication.instance() or QApplication([])
    dashboard = MinerDashboard(database, miner)
    dashboard.set_scenario_price("silver", 70)
    dashboard.set_development_risk_factor(0.8)
    dashboard.save_analysis_scenario()
    application.processEvents()

    scenario = database.list_analysis_scenarios(miner.id)[0]
    assert scenario.name == "Higher silver"
    assert scenario.metal_prices_usd["silver"] == 70
    assert scenario.development_risk_factor == 0.8
    dashboard.set_scenario_price("silver", 60)
    dashboard.load_analysis_scenario(scenario.id)
    assert dashboard.scenario_prices["silver"] == 70
    assert dashboard.development_risk_factor == 0.8
    dashboard.close()
    database.close()


def test_settings_dialog_persists_the_base_currency(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    application = QApplication.instance() or QApplication([])
    dialog = SettingsDialog(database)

    currency_input = dialog.findChild(QComboBox)
    assert currency_input is not None
    assert currency_input.currentText() == "SEK"
    currency_input.setCurrentText("USD")
    gold_input = dialog.findChild(QDoubleSpinBox, "default_scenario_gold_price_usd_per_ounce")
    silver_input = dialog.findChild(QDoubleSpinBox, "default_scenario_silver_price_usd_per_ounce")
    assert gold_input is not None
    assert silver_input is not None
    assert gold_input.value() == 6000
    assert silver_input.value() == 80
    gold_input.setValue(5500)
    silver_input.setValue(75)
    dialog.accept()
    application.processEvents()

    setting = database.get_current_application_setting("base_currency")
    assert setting is not None
    assert setting.value == "USD"
    assert database.get_current_application_setting("default_scenario_gold_price_usd_per_ounce").value == "5500"
    assert database.get_current_application_setting("default_scenario_silver_price_usd_per_ounce").value == "75"
    dialog.close()
    database.close()


def test_scenario_price_defaults_are_shared_across_miners(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    first_miner = database.add_miner("First Silver", "FSLV", "Silver", "Developer")
    second_miner = database.add_miner("Second Gold", "SGLD", "Gold", "Developer")
    database.set_application_setting("default_scenario_gold_price_usd_per_ounce", "5500")
    database.set_application_setting("default_scenario_silver_price_usd_per_ounce", "75")
    application = QApplication.instance() or QApplication([])
    first_dashboard = MinerDashboard(database, first_miner)
    second_dashboard = MinerDashboard(database, second_miner)

    assert first_dashboard._scenario_default_price("gold", 4_000) == 5500
    assert first_dashboard._scenario_default_price("silver", 60) == 75
    assert second_dashboard._scenario_default_price("gold", 4_000) == 5500
    assert second_dashboard._scenario_default_price("silver", 60) == 75

    first_dashboard.close()
    second_dashboard.close()
    application.processEvents()
    database.close()
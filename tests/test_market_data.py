from pathlib import Path

from gosimine.database import Database
from gosimine.market_data import COMMODITY_TICKERS, Quote, refresh_market_data


class FakeYahooFinanceClient:
    def __init__(self) -> None:
        self.quotes = {
            "VZLA": Quote(4.10, "USD", "2026-09-12T20:00:00+00:00"),
            "USDSEK=X": Quote(10.45, "SEK", "2026-09-12T20:00:00+00:00"),
            "CADSEK=X": Quote(7.70, "SEK", "2026-09-12T20:00:00+00:00"),
            "AUDSEK=X": Quote(6.95, "SEK", "2026-09-12T20:00:00+00:00"),
            "EURSEK=X": Quote(11.20, "SEK", "2026-09-12T20:00:00+00:00"),
            "SI=F": Quote(64.55, "USD", "2026-09-12T20:00:00+00:00"),
            "GC=F": Quote(4_366.20, "USD", "2026-09-12T20:00:00+00:00"),
            "HG=F": Quote(4.50, "USD", "2026-09-12T20:00:00+00:00"),
        }

    def get_quote(self, ticker: str) -> Quote:
        return self.quotes[ticker]

    def get_shares_outstanding(self, ticker: str) -> float:
        assert ticker in {"VZLA", "VZLA.TO"}
        return 355_056_872


def test_refresh_market_data_stores_vzla_price_and_required_currency_pair(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")

    refresh_market_data(database, miner, FakeYahooFinanceClient())

    price = database.get_latest_market_snapshot(miner.id)
    assert price is not None
    assert price.price == 4.10
    assert price.currency == "USD"
    rate = database.get_latest_exchange_rate("USD", "SEK")
    assert rate is not None
    assert rate.source == "Yahoo Finance"
    parameters = database.list_current_parameters(miner.id)
    assert any(
        parameter.parameter == "basic_shares_outstanding"
        and parameter.value == 355_056_872
        for parameter in parameters
    )
    for commodity in COMMODITY_TICKERS:
        price = database.get_latest_commodity_price(commodity)
        assert price is not None
        assert price.currency == "USD"
        assert price.unit == ("USD/lb" if commodity == "copper" else "USD/oz")
    database.close()


def test_refresh_market_data_uses_direct_pairs_for_trading_and_display_currencies(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    database.set_application_setting("base_currency", "AUD")
    miner = database.add_miner("Vizsla Silver", "VZLA.TO", "Silver", "Developer", "CAD")
    client = FakeYahooFinanceClient()
    client.quotes["VZLA.TO"] = Quote(5.00, "CAD", "2026-09-12T20:00:00+00:00")
    client.quotes["USDCAD=X"] = Quote(1.36, "CAD", "2026-09-12T20:00:00+00:00")
    client.quotes["CADAUD=X"] = Quote(1.10, "AUD", "2026-09-12T20:00:00+00:00")

    refresh_market_data(database, miner, client)

    assert database.get_latest_exchange_rate("USD", "CAD") is not None
    assert database.get_latest_exchange_rate("CAD", "AUD") is not None
    assert database.get_latest_exchange_rate("USD", "SEK") is None
    database.close()


def test_failed_refresh_preserves_existing_market_snapshot(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")
    existing = database.add_market_snapshot(
        miner.id,
        3.97,
        "USD",
        "2026-09-11T20:00:00+00:00",
        "2026-09-11T21:00:00+00:00",
        "Yahoo Finance",
    )

    class FailingYahooFinanceClient:
        def get_quote(self, ticker: str) -> Quote:
            raise ValueError("Yahoo Finance unavailable")

        def get_shares_outstanding(self, ticker: str) -> float:
            raise ValueError("Yahoo Finance unavailable")

    try:
        refresh_market_data(database, miner, FailingYahooFinanceClient())
    except ValueError:
        pass

    assert database.get_latest_market_snapshot(miner.id) == existing
    database.close()


def test_late_refresh_failure_does_not_write_partial_snapshots(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")
    miner = database.add_miner("Vizsla Silver", "VZLA", "Silver", "Developer")

    class LateFailingYahooFinanceClient:
        def get_quote(self, ticker: str) -> Quote:
            if ticker == "SI=F":
                raise ValueError("Silver quote unavailable")
            return Quote(4.10, "USD", "2026-09-12T20:00:00+00:00")

        def get_shares_outstanding(self, ticker: str) -> float:
            return 355_056_872

    with __import__("pytest").raises(ValueError, match="Silver quote unavailable"):
        refresh_market_data(database, miner, LateFailingYahooFinanceClient())

    assert database.get_latest_market_snapshot(miner.id) is None
    assert database.list_current_parameters(miner.id) == []
    assert database.get_latest_commodity_price("gold") is None
    database.close()
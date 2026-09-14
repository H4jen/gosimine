from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import yfinance as yf

from gosimine.commodities import COMMODITIES
from gosimine.database import Database, Miner
from gosimine.settings import BASE_CURRENCY

COMMODITY_TICKERS = {
    commodity: definition.yahoo_ticker for commodity, definition in COMMODITIES.items()
}


@dataclass(frozen=True)
class Quote:
    price: float
    currency: str
    market_timestamp: str


class YahooFinanceClient:
    def get_quote(self, ticker: str) -> Quote:
        yahoo_ticker = yf.Ticker(ticker)
        history = yahoo_ticker.history(period="1d", auto_adjust=False)
        if history.empty:
            raise ValueError(f"No market data returned for {ticker}")
        timestamp = history.index[-1].isoformat()
        return Quote(
            price=float(history.iloc[-1]["Close"]),
            currency=str(yahoo_ticker.fast_info["currency"]).upper(),
            market_timestamp=timestamp,
        )

    def get_shares_outstanding(self, ticker: str) -> float:
        shares = yf.Ticker(ticker).fast_info.get("shares")
        if shares is None or float(shares) <= 0:
            raise ValueError(f"No shares outstanding returned for {ticker}")
        return float(shares)


def currency_pair_ticker(from_currency: str, to_currency: str) -> str:
    return f"{from_currency.strip().upper()}{to_currency.strip().upper()}=X"


def display_currency(database: Database) -> str:
    setting = database.get_current_application_setting(BASE_CURRENCY.key)
    return setting.value if setting is not None else BASE_CURRENCY.default_value


def refresh_market_data(
    database: Database, miner: Miner, client: YahooFinanceClient | None = None
) -> None:
    yahoo = client or YahooFinanceClient()
    retrieved_at = datetime.now(UTC).isoformat()
    share_price = yahoo.get_quote(miner.ticker)
    shares = yahoo.get_shares_outstanding(miner.ticker)
    commodity_prices = []
    for commodity, ticker in COMMODITY_TICKERS.items():
        quote = yahoo.get_quote(ticker)
        commodity_prices.append(
            (
                commodity,
                quote.price,
                quote.currency,
                COMMODITIES[commodity].price_unit,
                quote.market_timestamp,
            )
        )
    currencies = {
        ("USD", miner.trading_currency),
        (miner.trading_currency, display_currency(database)),
    }
    exchange_rates = []
    for from_currency, to_currency in currencies:
        if from_currency == to_currency:
            continue
        ticker = currency_pair_ticker(from_currency, to_currency)
        quote = yahoo.get_quote(ticker)
        exchange_rates.append((from_currency, to_currency, quote.price))
    database.record_market_refresh(
        miner.id,
        share_price.price,
        share_price.currency,
        share_price.market_timestamp,
        shares,
        commodity_prices,
        exchange_rates,
        retrieved_at,
        "Yahoo Finance",
    )
from __future__ import annotations

from dataclasses import dataclass

import yfinance as yf


VZLA_TICKER = "VZLA"
SILVER_TICKER = "SI=F"
GOLD_TICKER = "GC=F"

# Panuco Feasibility Study, November 12, 2025.
PAYABLE_SILVER_OUNCES_PER_YEAR = 10_130_000
PAYABLE_GOLD_OUNCES_PER_YEAR = 83_000
PAYABLE_AGEQ_OUNCES_PER_YEAR = 17_383_000
AISC_USD_PER_AGEQ_OUNCE = 10.61
MINE_LIFE_YEARS = 9.4
AFTER_TAX_NPV_USD = 1_802_000_000

# The attached comparison table reports 1.01 AgEq oz/share for VZLA.
# This is an externally supplied comparison input, not annual FS output.
TABLE_AGEQ_OUNCES_PER_SHARE = 1.01
TABLE_AGEQ_PRICE_USD = 65.00


@dataclass(frozen=True)
class Quote:
    price: float
    timestamp: str


def latest_close(ticker: str) -> Quote:
    history = yf.Ticker(ticker).history(
        period="5d", interval="1d", auto_adjust=False, actions=False
    )
    history = history.dropna(subset=["Close"])
    if history.empty:
        raise RuntimeError(f"No daily close data for {ticker}")

    timestamp = history.index[-1]
    timestamp = (
        timestamp.tz_localize("UTC")
        if timestamp.tzinfo is None
        else timestamp.tz_convert("UTC")
    )
    return Quote(float(history.iloc[-1]["Close"]), timestamp.isoformat())


def current_shares_outstanding() -> int:
    shares = yf.Ticker(VZLA_TICKER).fast_info.get("shares")
    if shares is None or float(shares) <= 0:
        raise RuntimeError("Yahoo Finance did not provide VZLA shares outstanding")
    return int(shares)


def money(value: float) -> str:
    return f"${value:,.2f}"


def calculation_separator() -> None:
    print()
    print("-" * 49)
    print()


def main() -> None:
    vzla_quote = latest_close(VZLA_TICKER)
    silver_quote = latest_close(SILVER_TICKER)
    gold_quote = latest_close(GOLD_TICKER)
    shares = current_shares_outstanding()

    silver_value = PAYABLE_SILVER_OUNCES_PER_YEAR * silver_quote.price
    gold_value = PAYABLE_GOLD_OUNCES_PER_YEAR * gold_quote.price
    annual_metal_value = silver_value + gold_value
    live_ageq_price = annual_metal_value / PAYABLE_AGEQ_OUNCES_PER_YEAR
    annual_aisc_cost = PAYABLE_AGEQ_OUNCES_PER_YEAR * AISC_USD_PER_AGEQ_OUNCE
    annual_margin_proxy = annual_metal_value - annual_aisc_cost
    annual_ageq_ounces_per_share = PAYABLE_AGEQ_OUNCES_PER_YEAR / shares
    annual_margin_proxy_per_share = annual_margin_proxy / shares
    price_to_annual_proxy = vzla_quote.price / annual_margin_proxy_per_share
    annual_proxy_yield = annual_margin_proxy_per_share / vzla_quote.price

    lifetime_ageq_ounces = PAYABLE_AGEQ_OUNCES_PER_YEAR * MINE_LIFE_YEARS
    lifetime_margin_proxy = annual_margin_proxy * MINE_LIFE_YEARS
    lifetime_margin_proxy_per_share = lifetime_margin_proxy / shares
    lifetime_proxy_multiple = lifetime_margin_proxy_per_share / vzla_quote.price

    table_margin_per_ounce = TABLE_AGEQ_PRICE_USD - AISC_USD_PER_AGEQ_OUNCE
    table_lifetime_proxy_per_share = TABLE_AGEQ_OUNCES_PER_SHARE * table_margin_per_ounce
    table_factor = table_lifetime_proxy_per_share / vzla_quote.price
    table_implied_total_ounces = TABLE_AGEQ_OUNCES_PER_SHARE * shares

    project_npv_per_share = AFTER_TAX_NPV_USD / shares
    price_to_project_npv = vzla_quote.price / project_npv_per_share

    print("VZLA Panuco analysis (USD, read-only)")
    print("=" * 40)
    print("Market inputs from Yahoo Finance")
    print(f"VZLA close:                 {money(vzla_quote.price)} at {vzla_quote.timestamp}")
    print(f"Silver futures close:       {money(silver_quote.price)}/oz at {silver_quote.timestamp}")
    print(f"Gold futures close:         {money(gold_quote.price)}/oz at {gold_quote.timestamp}")
    print(f"Current basic shares:       {shares:,.0f} (Yahoo estimate; not fully diluted)")
    print()
    print("Panuco FS inputs (November 2025)")
    print(f"Payable silver:             {PAYABLE_SILVER_OUNCES_PER_YEAR:,.0f} oz/year")
    print(f"Payable gold:               {PAYABLE_GOLD_OUNCES_PER_YEAR:,.0f} oz/year")
    print(f"Payable AgEq:               {PAYABLE_AGEQ_OUNCES_PER_YEAR:,.0f} oz/year")
    print(f"AISC:                       {money(AISC_USD_PER_AGEQ_OUNCE)}/AgEq oz")
    print(f"Mine life:                  {MINE_LIFE_YEARS:.1f} years")
    print(f"After-tax NPV(5%):          {money(AFTER_TAX_NPV_USD)}")
    print()
    print("Annual FS-plan proxy at current metal prices")
    print(
        "Silver value = payable silver oz/year x live silver price\n"
        f"             = {PAYABLE_SILVER_OUNCES_PER_YEAR:,.0f} x {money(silver_quote.price)}"
    )
    print(f"Silver value:               {money(silver_value)}")
    calculation_separator()
    print(
        "Gold value = payable gold oz/year x live gold price\n"
        f"           = {PAYABLE_GOLD_OUNCES_PER_YEAR:,.0f} x {money(gold_quote.price)}"
    )
    print(f"Gold value:                 {money(gold_value)}")
    calculation_separator()
    print(
        "Total metal value = silver value + gold value\n"
        f"                  = {money(silver_value)} + {money(gold_value)}"
    )
    print(f"Total metal value:          {money(annual_metal_value)}")
    calculation_separator()
    print(
        "Live FS-mix AgEq price = total metal value / payable AgEq oz/year\n"
        f"                        = {money(annual_metal_value)} / {PAYABLE_AGEQ_OUNCES_PER_YEAR:,.0f}"
    )
    print(f"Live FS-mix AgEq price:     {money(live_ageq_price)}/AgEq oz")
    calculation_separator()
    print(
        "AISC cost proxy = payable AgEq oz/year x AISC/AgEq oz\n"
        f"                = {PAYABLE_AGEQ_OUNCES_PER_YEAR:,.0f} x {money(AISC_USD_PER_AGEQ_OUNCE)}"
    )
    print(f"AISC cost proxy:            {money(annual_aisc_cost)}")
    calculation_separator()
    print(
        "Margin proxy = total metal value - AISC cost proxy\n"
        f"             = {money(annual_metal_value)} - {money(annual_aisc_cost)}"
    )
    print(f"Margin proxy:               {money(annual_margin_proxy)}")
    calculation_separator()
    print(
        "Annual AgEq oz/share = payable AgEq oz/year / current basic shares\n"
        f"                     = {PAYABLE_AGEQ_OUNCES_PER_YEAR:,.0f} / {shares:,.0f}"
    )
    print(f"Annual AgEq oz/share:       {annual_ageq_ounces_per_share:.4f}")
    calculation_separator()
    print(
        "Annual margin proxy/share = annual margin proxy / current basic shares\n"
        f"                          = {money(annual_margin_proxy)} / {shares:,.0f}"
    )
    print(f"Annual margin proxy/share:  {money(annual_margin_proxy_per_share)}")
    calculation_separator()
    print(
        "Price / annual proxy = VZLA share price / annual margin proxy/share\n"
        f"                     = {money(vzla_quote.price)} / {money(annual_margin_proxy_per_share)}"
    )
    print(f"Price / annual proxy:       {price_to_annual_proxy:.2f}x")
    calculation_separator()
    print(
        "Annual proxy yield = annual margin proxy/share / VZLA share price\n"
        f"                   = {money(annual_margin_proxy_per_share)} / {money(vzla_quote.price)}"
    )
    print(f"Annual proxy yield:         {annual_proxy_yield:.1%}")
    calculation_separator()
    print("Lifetime undiscounted FS-plan proxy")
    print(
        "Lifetime AgEq ounces = payable AgEq oz/year x mine life\n"
        f"                      = {PAYABLE_AGEQ_OUNCES_PER_YEAR:,.0f} x {MINE_LIFE_YEARS:.1f}"
    )
    print(f"Lifetime AgEq ounces:       {lifetime_ageq_ounces:,.0f}")
    calculation_separator()
    print(
        "Lifetime AgEq oz/share = lifetime AgEq ounces / current basic shares\n"
        f"                       = {lifetime_ageq_ounces:,.0f} / {shares:,.0f}"
    )
    print(f"Lifetime AgEq oz/share:     {lifetime_ageq_ounces / shares:.4f}")
    calculation_separator()
    print(
        "Lifetime margin proxy = annual margin proxy x mine life\n"
        f"                      = {money(annual_margin_proxy)} x {MINE_LIFE_YEARS:.1f}"
    )
    print(f"Lifetime margin proxy:      {money(lifetime_margin_proxy)}")
    calculation_separator()
    print(
        "Lifetime proxy/share = lifetime margin proxy / current basic shares\n"
        f"                     = {money(lifetime_margin_proxy)} / {shares:,.0f}"
    )
    print(f"Lifetime proxy/share:       {money(lifetime_margin_proxy_per_share)}")
    calculation_separator()
    print(
        "Lifetime proxy / price = lifetime proxy/share / VZLA share price\n"
        f"                       = {money(lifetime_margin_proxy_per_share)} / {money(vzla_quote.price)}"
    )
    print(f"Lifetime proxy / price:     {lifetime_proxy_multiple:.2f}x")
    calculation_separator()
    print("Project-NPV reference")
    print(
        "Unadjusted NPV/share = after-tax NPV(5%) / current basic shares\n"
        f"                     = {money(AFTER_TAX_NPV_USD)} / {shares:,.0f}"
    )
    print(f"Unadjusted NPV/share:       {money(project_npv_per_share)}")
    calculation_separator()
    print(
        "Price / NPV = VZLA share price / unadjusted NPV/share\n"
        f"            = {money(vzla_quote.price)} / {money(project_npv_per_share)}"
    )
    print(f"Price / NPV:                {price_to_project_npv:.2f}x")
    calculation_separator()
    print("Attached-table 13x reconstruction")
    print(
        "Implied total AgEq ounces = table AgEq oz/share x current basic shares\n"
        f"                          = {TABLE_AGEQ_OUNCES_PER_SHARE:.2f} x {shares:,.0f}"
    )
    print(f"Table AgEq ounces/share:    {TABLE_AGEQ_OUNCES_PER_SHARE:.2f}")
    print(f"Implied total AgEq ounces:  {table_implied_total_ounces:,.0f}")
    calculation_separator()
    print(
        "Table margin/AgEq oz = table AgEq price - AISC/AgEq oz\n"
        f"                     = {money(TABLE_AGEQ_PRICE_USD)} - {money(AISC_USD_PER_AGEQ_OUNCE)}"
    )
    print(f"Table margin/AgEq oz:       {money(table_margin_per_ounce)}")
    calculation_separator()
    print(
        "Table proxy/share = table AgEq oz/share x table margin/AgEq oz\n"
        f"                  = {TABLE_AGEQ_OUNCES_PER_SHARE:.2f} x {money(table_margin_per_ounce)}"
    )
    print(f"Table proxy/share:          {money(table_lifetime_proxy_per_share)}")
    calculation_separator()
    print(
        "Table factor = table proxy/share / VZLA share price\n"
        f"             = {money(table_lifetime_proxy_per_share)} / {money(vzla_quote.price)}"
    )
    print(f"Table factor at VZLA close: {table_factor:.2f}x")
    calculation_separator()
    print("This 13x-style figure is a lifetime, undiscounted screening ratio.")
    print("It is not annual earnings, NAV, or a risk-adjusted target price.")


if __name__ == "__main__":
    main()
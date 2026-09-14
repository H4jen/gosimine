from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date
from pathlib import Path
from typing import Protocol


class YahooFinanceClient(Protocol):
    def get_quote(self, ticker: str): ...

    def get_shares_outstanding(self, ticker: str) -> float: ...


REQUIRED_COLUMNS = (
    "ticker",
    "name",
    "trading_currency",
    "primary_commodity",
    "stage",
    "lifecycle_status",
)
REQUIRED_PARAMETERS = {
    "basic_shares_outstanding": ("shares", "shares"),
}
OPTIONAL_PARAMETERS = {
    "annual_production_ounces": ("equivalent_production", "project_study"),
    "aisc_per_ounce": ("equivalent_aisc", "project_study"),
    "mine_life_years": ("years", "project_study"),
    "measured_indicated_resource_equivalent_ounces": ("equivalent_resource", "resource"),
    "inferred_resource_equivalent_ounces": ("equivalent_resource", "resource"),
    "total_resource_equivalent_ounces": ("equivalent_resource", "resource"),
    "study_discount_rate_percent": ("%", "project_study"),
    "potential_conversion_shares": ("shares", "dilution"),
    "potential_dilution_shares": ("shares", "dilution"),
}
CURRENCY_PARAMETERS = {
    "after_tax_npv": "project_study",
    "cash": "financial",
    "total_debt": "financial",
}
EVIDENCE_GROUPS = ("project_study", "resource", "financial", "dilution", "shares")
MISSING_SOURCE = "Source missing"
MISSING_DATE = "1900-01-01"
OPTIONAL_DATE_EVIDENCE_GROUPS = {"project_study", "dilution"}
TICKER_PATTERN = re.compile(r"[A-Z0-9][A-Z0-9.-]*")
PAYABLE_METAL_PATTERN = re.compile(r"annual_payable_([a-z]+)_(ounces|pounds)")
STUDY_METAL_PRICE_PATTERN = re.compile(
    r"study_metal_price_([a-z]+)_usd_per_(ounce|pound)"
)
CURRENCY_PATTERN = re.compile(r"[A-Z]{3}")


def evidence_columns(evidence_group: str) -> tuple[str, str]:
    return f"{evidence_group}_as_of_date", f"{evidence_group}_source"


def equivalent_unit(unit: str, primary_commodity: str) -> str:
    prefix = {"gold": "AuEq", "silver": "AgEq"}.get(primary_commodity.lower(), "Eq")
    return {
        "equivalent_production": f"{prefix} oz/year",
        "equivalent_aisc": f"USD/{prefix} oz",
        "equivalent_resource": f"{prefix} oz",
    }.get(unit, unit)


def parse_parameter(
    row: dict[str, str],
    parameter: str,
    unit: str,
    evidence_group: str,
    row_number: int,
    allow_zero: bool = False,
) -> dict[str, object]:
    date_column, source_column = evidence_columns(evidence_group)
    missing_values = [
        column
        for column in (parameter,)
        if not (row.get(column) or "").strip()
    ]
    if not row[date_column] and evidence_group not in OPTIONAL_DATE_EVIDENCE_GROUPS:
        missing_values.append(date_column)
    if missing_values:
        raise ValueError(
            f"Row {row_number} is missing required parameter values: {', '.join(missing_values)}"
        )
    try:
        value = float(row[parameter])
    except ValueError as error:
        raise ValueError(f"Row {row_number} has an invalid {parameter} value.") from error
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError(f"Row {row_number} must have a positive {parameter} value.")
    try:
        date.fromisoformat(row[date_column] or MISSING_DATE)
    except ValueError as error:
        raise ValueError(f"Row {row_number} has an invalid {date_column} date.") from error
    return {
        "name": parameter,
        "value": value,
        "unit": unit,
        "as_of_date": row[date_column] or MISSING_DATE,
        "source": row[source_column] or MISSING_SOURCE,
    }


def parse_currency_parameter(
    row: dict[str, str], parameter: str, evidence_group: str, row_number: int
) -> dict[str, object]:
    currency = row[f"{parameter}_currency"].upper()
    if not CURRENCY_PATTERN.fullmatch(currency):
        raise ValueError(f"Row {row_number} has an invalid {parameter}_currency value.")
    snapshot = parse_parameter(
        row,
        parameter,
        currency,
        evidence_group,
        row_number,
        allow_zero=parameter == "total_debt",
    )
    snapshot["name"] = f"{parameter}_{currency.lower()}"
    return snapshot


def parse_intake(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as intake_file:
        reader = csv.DictReader(intake_file)
        if reader.fieldnames is None:
            raise ValueError("Miner intake CSV must include a header row.")
        required_columns = set(REQUIRED_COLUMNS)
        for parameter in REQUIRED_PARAMETERS | OPTIONAL_PARAMETERS:
            required_columns.add(parameter)
        for parameter in CURRENCY_PARAMETERS:
            required_columns.update((parameter, f"{parameter}_currency"))
        for evidence_group in EVIDENCE_GROUPS:
            required_columns.update(evidence_columns(evidence_group))
        missing_columns = required_columns - set(reader.fieldnames)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Miner intake CSV is missing required columns: {missing}")

        payable_parameters = [
            column
            for column in reader.fieldnames
            if PAYABLE_METAL_PATTERN.fullmatch(column)
        ]
        if not payable_parameters:
            raise ValueError("Miner intake CSV must include an annual_payable_<metal>_ounces column.")
        study_price_parameters = [
            column
            for column in reader.fieldnames
            if STUDY_METAL_PRICE_PATTERN.fullmatch(column)
        ]
        if not study_price_parameters:
            raise ValueError(
                "Miner intake CSV must include a study_metal_price_<metal>_usd_per_ounce column."
            )

        records = []
        tickers = set()
        for row_number, row in enumerate(reader, start=2):
            values = {column: (row[column] or "").strip() for column in reader.fieldnames}
            record = {column: values[column] for column in REQUIRED_COLUMNS}
            missing_values = [column for column, value in record.items() if not value]
            if missing_values:
                missing = ", ".join(missing_values)
                raise ValueError(f"Row {row_number} is missing required values: {missing}")
            record["ticker"] = record["ticker"].upper()
            record["trading_currency"] = record["trading_currency"].upper()
            if not TICKER_PATTERN.fullmatch(record["ticker"]):
                raise ValueError(f"Row {row_number} has an invalid ticker: {record['ticker']}")
            if record["ticker"] in tickers:
                raise ValueError(f"Duplicate ticker in miner intake: {record['ticker']}")
            tickers.add(record["ticker"])
            parameters = [
                parse_parameter(
                    values,
                    parameter,
                    equivalent_unit(unit, record["primary_commodity"]),
                    evidence_group,
                    row_number,
                )
                for parameter, (unit, evidence_group) in REQUIRED_PARAMETERS.items()
            ]
            parameters.extend(
                parse_parameter(
                    values,
                    parameter,
                    equivalent_unit(unit, record["primary_commodity"]),
                    evidence_group,
                    row_number,
                )
                for parameter, (unit, evidence_group) in OPTIONAL_PARAMETERS.items()
                if values[parameter]
            )
            parameters.extend(
                parse_currency_parameter(values, parameter, evidence_group, row_number)
                for parameter, evidence_group in CURRENCY_PARAMETERS.items()
                if values[parameter] or values[f"{parameter}_currency"]
            )
            for parameter in payable_parameters:
                if values[parameter]:
                    metal, quantity = PAYABLE_METAL_PATTERN.fullmatch(parameter).groups()
                    symbol = {"gold": "Au", "silver": "Ag", "copper": "Cu"}.get(
                        metal, metal.title()
                    )
                    unit = f"{symbol} {'oz' if quantity == 'ounces' else 'lb'}/year"
                    parameters.append(
                        parse_parameter(values, parameter, unit, "project_study", row_number)
                    )
            for parameter in study_price_parameters:
                if values[parameter]:
                    quantity = STUDY_METAL_PRICE_PATTERN.fullmatch(parameter).group(2)
                    parameters.append(
                        parse_parameter(
                            values,
                            parameter,
                            f"USD/{'oz' if quantity == 'ounce' else 'lb'}",
                            "project_study",
                            row_number,
                        )
                    )
            records.append(
                {
                    "name": record["name"],
                    "ticker": record["ticker"],
                    "trading_currency": record["trading_currency"],
                    "primary_commodity": record["primary_commodity"],
                    "stage": record["stage"],
                    "lifecycle_status": {
                        "value": record["lifecycle_status"],
                        "as_of_date": values["project_study_as_of_date"] or MISSING_DATE,
                        "source": values["project_study_source"] or MISSING_SOURCE,
                    },
                    "parameters": parameters,
                }
            )
    return records


def validate_yahoo_listings(
    records: list[dict[str, object]], yahoo: YahooFinanceClient
) -> None:
    for record in records:
        ticker = str(record["ticker"])
        expected_currency = str(record["trading_currency"])
        try:
            quote = yahoo.get_quote(ticker)
            shares = yahoo.get_shares_outstanding(ticker)
        except Exception as error:
            raise ValueError(f"Yahoo Finance validation failed for {ticker}: {error}") from error
        if quote.price <= 0:
            raise ValueError(f"Yahoo Finance returned a non-positive quote for {ticker}.")
        if quote.currency != expected_currency:
            raise ValueError(
                f"Yahoo Finance currency mismatch for {ticker}: "
                f"expected {expected_currency}, received {quote.currency}."
            )
        if shares <= 0:
            raise ValueError(f"Yahoo Finance returned no positive share count for {ticker}.")


def build_seed(
    intake_path: Path,
    output_directory: Path,
    verify_yahoo: bool = False,
    yahoo_client: YahooFinanceClient | None = None,
) -> list[Path]:
    records = parse_intake(intake_path)
    if verify_yahoo:
        if yahoo_client is None:
            from gosimine.market_data import YahooFinanceClient as LiveYahooFinanceClient

            yahoo_client = LiveYahooFinanceClient()
        validate_yahoo_listings(records, yahoo_client)
    output_directory.mkdir(parents=True, exist_ok=True)
    created_paths = []
    for record in records:
        filename = record["ticker"].replace(".", "_")
        output_path = output_directory / f"{filename}.json"
        if output_path.exists():
            continue
        output_path.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        created_paths.append(output_path)
    return created_paths


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Obsolete: create per-miner seed JSON files from a legacy CSV intake."
    )
    parser.add_argument(
        "--intake",
        type=Path,
        default=project_root / "seed" / "miner_intake.csv",
        help="Obsolete legacy CSV intake; new dossiers are authored in seed/miners JSON files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "seed" / "miners",
        help="Directory for one JSON seed object per miner.",
    )
    parser.add_argument(
        "--verify-yahoo",
        action="store_true",
        help="Validate each ticker's live Yahoo Finance quote, currency, and share count.",
    )
    arguments = parser.parse_args()

    try:
        created_paths = build_seed(
            arguments.intake, arguments.output, verify_yahoo=arguments.verify_yahoo
        )
    except (FileNotFoundError, ValueError, FileExistsError) as error:
        parser.error(str(error))
    for created_path in created_paths:
        print(created_path)


if __name__ == "__main__":
    main()
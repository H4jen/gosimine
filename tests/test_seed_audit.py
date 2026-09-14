import json
from pathlib import Path

from gosimine.seed_audit import audit_seed_record, full_analysis_missing_inputs


def test_audit_abra_seed_identifies_only_runtime_requirements() -> None:
    seed_path = Path(__file__).parents[1] / "seed" / "miners" / "ABRA_TO.json"
    record = json.loads(seed_path.read_text())
    results = {result.metric: result for result in audit_seed_record(record)}
    seed_missing, runtime_missing = full_analysis_missing_inputs(record)

    assert seed_missing == ()
    assert runtime_missing == (
        "market share price",
        "USD-to-listing-currency FX rate",
        "USD gold price",
        "USD silver price",
    )
    assert results["AISC"].ready
    assert results["Mine life"].ready
    assert results["NAV / share"].missing == (
        "market share price",
        "USD-to-listing-currency FX rate",
        "USD gold price",
        "USD silver price",
    )
    assert results["Resource AgEq oz / share"].missing == results["NAV / share"].missing


def test_audit_identifies_missing_seed_parameters_per_metric() -> None:
    seed_missing, runtime_missing = full_analysis_missing_inputs(
        {"ticker": "EMPTY", "parameters": []}
    )
    results = {
        result.metric: result
        for result in audit_seed_record({"ticker": "EMPTY", "parameters": []})
    }

    assert seed_missing == (
        "annual_production_ounces",
        "aisc_per_ounce",
        "mine_life_years",
        "basic_shares_outstanding",
        "after_tax_npv_usd",
        "total_resource_equivalent_ounces",
        "annual_payable_<metal>_ounces or annual_payable_<metal>_pounds",
        "cash_<currency>",
        "total_debt_<currency>",
    )
    assert runtime_missing == ("market share price",)
    assert results["AISC"].missing == ("aisc_per_ounce",)
    assert results["Annual margin / share"].missing == (
        "annual_production_ounces",
        "aisc_per_ounce",
        "mine_life_years",
        "basic_shares_outstanding",
        "annual_payable_<metal>_ounces or annual_payable_<metal>_pounds",
        "market share price",
    )
    assert results["NAV / share"].missing[-3:] == (
        "after_tax_npv_usd",
        "cash_<currency>",
        "total_debt_<currency>",
    )
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class MetricReadiness:
    metric: str
    missing: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.missing


CORE_PARAMETERS = (
    "annual_production_ounces",
    "aisc_per_ounce",
    "mine_life_years",
    "basic_shares_outstanding",
)
FULL_ANALYSIS_PARAMETERS = (
    *CORE_PARAMETERS,
    "after_tax_npv_usd",
    "total_resource_equivalent_ounces",
)


def audit_seed_record(record: Mapping[str, object]) -> list[MetricReadiness]:
    parameters = _parameter_names(record.get("parameters", []))
    payable_metals = _payable_metals(parameters)
    core_missing = list(_missing_parameters(parameters, CORE_PARAMETERS))
    if not payable_metals:
        core_missing.append("annual_payable_<metal>_ounces or annual_payable_<metal>_pounds")

    runtime_missing = ["market share price"]
    if str(record.get("trading_currency", "USD")).upper() != "USD":
        runtime_missing.append("USD-to-listing-currency FX rate")
    runtime_missing.extend(f"USD {metal} price" for metal in payable_metals)

    core_analysis_missing = tuple(core_missing + runtime_missing)
    npv_missing = _combine(core_analysis_missing, _missing_parameters(parameters, ("after_tax_npv_usd",)))
    nav_missing = _combine(
        npv_missing,
        _missing_financial_parameter(parameters, "cash"),
        _missing_financial_parameter(parameters, "total_debt"),
    )
    resource_missing = _combine(
        core_analysis_missing,
        _missing_parameters(parameters, ("total_resource_equivalent_ounces",)),
    )

    return [
        MetricReadiness("Share price", ("market share price",)),
        MetricReadiness("Annual margin / share", core_analysis_missing),
        MetricReadiness("AgEq price", core_analysis_missing),
        MetricReadiness("Margin per AgEq oz", core_analysis_missing),
        MetricReadiness("Annual AgEq oz / share", core_analysis_missing),
        MetricReadiness("Lifetime AgEq oz / share", core_analysis_missing),
        MetricReadiness("After-tax NPV / share", npv_missing),
        MetricReadiness("NPV / SP", npv_missing),
        MetricReadiness("NAV / share", nav_missing),
        MetricReadiness("NAV / SP", nav_missing),
        MetricReadiness("Risked NAV / share", nav_missing),
        MetricReadiness("Risked NAV / SP", nav_missing),
        MetricReadiness("Lifetime margin / share", core_analysis_missing),
        MetricReadiness("Lifetime margin / SP", core_analysis_missing),
        MetricReadiness("AISC", _missing_parameters(parameters, ("aisc_per_ounce",))),
        MetricReadiness("Mine life", _missing_parameters(parameters, ("mine_life_years",))),
        MetricReadiness("Resource AgEq oz / share", resource_missing),
        MetricReadiness("Resource margin / SP", resource_missing),
        MetricReadiness("Future annual margin / share", core_analysis_missing),
        MetricReadiness("Future lifetime margin / share", core_analysis_missing),
        MetricReadiness("Future lifetime margin / SP", core_analysis_missing),
        MetricReadiness("Future resource margin / SP", resource_missing),
    ]


def full_analysis_missing_inputs(record: Mapping[str, object]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    parameters = _parameter_names(record.get("parameters", []))
    seed_missing = list(_missing_parameters(parameters, FULL_ANALYSIS_PARAMETERS))
    payable_metals = _payable_metals(parameters)
    if not payable_metals:
        seed_missing.append("annual_payable_<metal>_ounces or annual_payable_<metal>_pounds")
    seed_missing.extend(_missing_financial_parameter(parameters, "cash"))
    seed_missing.extend(_missing_financial_parameter(parameters, "total_debt"))

    runtime_missing = ["market share price"]
    if str(record.get("trading_currency", "USD")).upper() != "USD":
        runtime_missing.append("USD-to-listing-currency FX rate")
    runtime_missing.extend(f"USD {metal} price" for metal in payable_metals)
    return tuple(seed_missing), tuple(runtime_missing)


def _parameter_names(parameters: object) -> set[str]:
    if not isinstance(parameters, list):
        return set()
    return {
        str(parameter["name"])
        for parameter in parameters
        if isinstance(parameter, Mapping) and isinstance(parameter.get("name"), str)
    }


def _payable_metals(parameters: Iterable[str]) -> list[str]:
    metals = []
    for parameter in parameters:
        match = re.fullmatch(r"annual_payable_([a-z]+)_(?:ounces|pounds)", parameter)
        if match:
            metals.append(match.group(1))
    return sorted(metals)


def _missing_parameters(parameters: set[str], required: Iterable[str]) -> tuple[str, ...]:
    return tuple(parameter for parameter in required if parameter not in parameters)


def _missing_financial_parameter(parameters: set[str], prefix: str) -> tuple[str, ...]:
    if any(parameter.startswith(f"{prefix}_") for parameter in parameters):
        return ()
    return (f"{prefix}_<currency>",)


def _combine(*groups: Iterable[str]) -> tuple[str, ...]:
    return tuple(item for group in groups for item in group)
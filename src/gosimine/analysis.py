from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class AnalysisInputs:
    annual_payable_metal_volumes: Mapping[str, float]
    metal_prices_usd: Mapping[str, float]
    annual_equivalent_ounces: float
    aisc_usd_per_equivalent_ounce: float
    mine_life_years: float
    shares_outstanding: float
    share_price_usd: float
    total_resource_equivalent_ounces: float | None = None
    after_tax_npv_usd: float | None = None
    cash_usd: float | None = None
    total_debt_usd: float | None = None
    development_risk_factor: float | None = None
    additional_dilution_shares: float = 0
    potential_conversion_shares: float | None = None


@dataclass(frozen=True)
class AnalysisResult:
    annual_metal_value_usd: float
    equivalent_price_usd_per_ounce: float
    margin_usd_per_equivalent_ounce: float
    annual_margin_usd: float
    annual_equivalent_ounces_per_share: float
    annual_margin_usd_per_share: float
    price_to_annual_margin: float
    annual_margin_yield: float
    lifetime_equivalent_ounces: float
    lifetime_equivalent_ounces_per_share: float
    lifetime_margin_usd: float
    lifetime_margin_usd_per_share: float
    lifetime_margin_to_price: float
    resource_equivalent_ounces_per_share: float | None
    resource_margin_to_price: float | None
    npv_usd_per_share: float | None
    npv_to_price: float | None
    equity_nav_usd: float | None
    equity_nav_usd_per_share: float | None
    equity_nav_to_price: float | None
    risked_nav_usd_per_share: float | None
    risked_nav_to_price: float | None
    diluted_shares_outstanding: float
    diluted_equity_nav_usd_per_share: float | None
    diluted_risked_nav_usd_per_share: float | None
    fully_converted_shares_outstanding: float | None
    fully_converted_equity_nav_usd_per_share: float | None
    fully_converted_risked_nav_usd_per_share: float | None


def calculate_analysis(inputs: AnalysisInputs) -> AnalysisResult:
    _require_positive("annual_equivalent_ounces", inputs.annual_equivalent_ounces)
    _require_positive("aisc_usd_per_equivalent_ounce", inputs.aisc_usd_per_equivalent_ounce)
    _require_positive("mine_life_years", inputs.mine_life_years)
    _require_positive("shares_outstanding", inputs.shares_outstanding)
    _require_positive("share_price_usd", inputs.share_price_usd)

    annual_metal_value = 0.0
    for metal, volume in inputs.annual_payable_metal_volumes.items():
        _require_positive(f"annual_payable_metal_volumes[{metal}]", volume)
        try:
            price = inputs.metal_prices_usd[metal]
        except KeyError as error:
            raise ValueError(f"Missing current price for {metal}") from error
        _require_positive(f"metal_prices_usd[{metal}]", price)
        annual_metal_value += volume * price

    equivalent_price = annual_metal_value / inputs.annual_equivalent_ounces
    margin_per_ounce = equivalent_price - inputs.aisc_usd_per_equivalent_ounce
    annual_margin = annual_metal_value - (
        inputs.annual_equivalent_ounces * inputs.aisc_usd_per_equivalent_ounce
    )
    annual_equivalent_ounces_per_share = (
        inputs.annual_equivalent_ounces / inputs.shares_outstanding
    )
    annual_margin_per_share = annual_margin / inputs.shares_outstanding
    lifetime_equivalent_ounces = inputs.annual_equivalent_ounces * inputs.mine_life_years
    lifetime_margin = annual_margin * inputs.mine_life_years
    lifetime_margin_per_share = lifetime_margin / inputs.shares_outstanding
    if inputs.total_resource_equivalent_ounces is not None:
        _require_positive(
            "total_resource_equivalent_ounces", inputs.total_resource_equivalent_ounces
        )
    resource_equivalent_ounces_per_share = (
        inputs.total_resource_equivalent_ounces / inputs.shares_outstanding
        if inputs.total_resource_equivalent_ounces is not None
        else None
    )
    resource_margin_to_price = (
        resource_equivalent_ounces_per_share * margin_per_ounce / inputs.share_price_usd
        if resource_equivalent_ounces_per_share is not None
        else None
    )

    npv_per_share = (
        inputs.after_tax_npv_usd / inputs.shares_outstanding
        if inputs.after_tax_npv_usd is not None
        else None
    )
    equity_nav = None
    if (
        inputs.after_tax_npv_usd is not None
        and inputs.cash_usd is not None
        and inputs.total_debt_usd is not None
    ):
        equity_nav = inputs.after_tax_npv_usd + inputs.cash_usd - inputs.total_debt_usd
    if inputs.development_risk_factor is not None and not 0 < inputs.development_risk_factor <= 1:
        raise ValueError("development_risk_factor must be greater than zero and at most one")
    if inputs.additional_dilution_shares < 0:
        raise ValueError("additional_dilution_shares must not be negative")
    if inputs.potential_conversion_shares is not None:
        _require_positive("potential_conversion_shares", inputs.potential_conversion_shares)
    diluted_shares = inputs.shares_outstanding + inputs.additional_dilution_shares
    equity_nav_per_share = (
        equity_nav / inputs.shares_outstanding if equity_nav is not None else None
    )
    diluted_equity_nav_per_share = (
        equity_nav / diluted_shares if equity_nav is not None else None
    )
    risked_nav_per_share = (
        equity_nav_per_share * inputs.development_risk_factor
        if equity_nav_per_share is not None and inputs.development_risk_factor is not None
        else None
    )
    diluted_risked_nav_per_share = (
        diluted_equity_nav_per_share * inputs.development_risk_factor
        if diluted_equity_nav_per_share is not None and inputs.development_risk_factor is not None
        else None
    )
    fully_converted_shares = (
        inputs.shares_outstanding + inputs.potential_conversion_shares
        if inputs.potential_conversion_shares is not None
        else None
    )
    fully_converted_equity_nav_per_share = (
        equity_nav / fully_converted_shares
        if equity_nav is not None and fully_converted_shares is not None
        else None
    )
    fully_converted_risked_nav_per_share = (
        fully_converted_equity_nav_per_share * inputs.development_risk_factor
        if fully_converted_equity_nav_per_share is not None
        and inputs.development_risk_factor is not None
        else None
    )
    return AnalysisResult(
        annual_metal_value_usd=annual_metal_value,
        equivalent_price_usd_per_ounce=equivalent_price,
        margin_usd_per_equivalent_ounce=margin_per_ounce,
        annual_margin_usd=annual_margin,
        annual_equivalent_ounces_per_share=annual_equivalent_ounces_per_share,
        annual_margin_usd_per_share=annual_margin_per_share,
        price_to_annual_margin=inputs.share_price_usd / annual_margin_per_share,
        annual_margin_yield=annual_margin_per_share / inputs.share_price_usd,
        lifetime_equivalent_ounces=lifetime_equivalent_ounces,
        lifetime_equivalent_ounces_per_share=(
            lifetime_equivalent_ounces / inputs.shares_outstanding
        ),
        lifetime_margin_usd=lifetime_margin,
        lifetime_margin_usd_per_share=lifetime_margin_per_share,
        lifetime_margin_to_price=lifetime_margin_per_share / inputs.share_price_usd,
        resource_equivalent_ounces_per_share=resource_equivalent_ounces_per_share,
        resource_margin_to_price=resource_margin_to_price,
        npv_usd_per_share=npv_per_share,
        npv_to_price=(npv_per_share / inputs.share_price_usd if npv_per_share else None),
        equity_nav_usd=equity_nav,
        equity_nav_usd_per_share=equity_nav_per_share,
        equity_nav_to_price=(
            equity_nav_per_share / inputs.share_price_usd if equity_nav_per_share else None
        ),
        risked_nav_usd_per_share=risked_nav_per_share,
        risked_nav_to_price=(
            risked_nav_per_share / inputs.share_price_usd if risked_nav_per_share else None
        ),
        diluted_shares_outstanding=diluted_shares,
        diluted_equity_nav_usd_per_share=diluted_equity_nav_per_share,
        diluted_risked_nav_usd_per_share=diluted_risked_nav_per_share,
        fully_converted_shares_outstanding=fully_converted_shares,
        fully_converted_equity_nav_usd_per_share=fully_converted_equity_nav_per_share,
        fully_converted_risked_nav_usd_per_share=fully_converted_risked_nav_per_share,
    )


def _require_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
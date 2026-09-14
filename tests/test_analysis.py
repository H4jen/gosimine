import pytest

from gosimine.analysis import (
    AnalysisInputs,
    ProjectInputs,
    calculate_analysis,
    consolidate_project_inputs,
)


def test_calculate_analysis_with_vizsla_inputs() -> None:
    result = calculate_analysis(
        AnalysisInputs(
            annual_payable_metal_volumes={"silver": 10_130_000, "gold": 83_000},
            metal_prices_usd={"silver": 64.5540008545, "gold": 4_366.2001953125},
            annual_equivalent_ounces=17_383_000,
            aisc_usd_per_equivalent_ounce=10.61,
            mine_life_years=9.4,
            shares_outstanding=355_056_872,
            share_price_usd=3.97,
            total_resource_equivalent_ounces=361_100_000,
            after_tax_npv_usd=1_802_000_000,
            cash_usd=406_495_000,
            total_debt_usd=240_366_000,
            development_risk_factor=0.70,
            additional_dilution_shares=20_000_000,
            potential_conversion_shares=51_391_860,
        )
    )

    assert result.annual_metal_value_usd == pytest.approx(1_016_326_644.87)
    assert result.equivalent_price_usd_per_ounce == pytest.approx(58.4667)
    assert result.annual_margin_usd_per_share == pytest.approx(2.342985)
    assert result.lifetime_margin_to_price == pytest.approx(5.54762)
    assert result.resource_equivalent_ounces_per_share == pytest.approx(1.017020)
    assert result.resource_margin_to_price == pytest.approx(12.259755)
    assert result.npv_usd_per_share == pytest.approx(5.075243)
    assert result.npv_to_price == pytest.approx(1.278398)
    assert result.equity_nav_usd == 1_968_129_000
    assert result.equity_nav_usd_per_share == pytest.approx(5.543137)
    assert result.equity_nav_to_price == pytest.approx(1.396256)
    assert result.risked_nav_usd_per_share == pytest.approx(3.880196)
    assert result.risked_nav_to_price == pytest.approx(0.977379)
    assert result.diluted_shares_outstanding == 375_056_872
    assert result.diluted_equity_nav_usd_per_share == pytest.approx(5.247548)
    assert result.diluted_risked_nav_usd_per_share == pytest.approx(3.673284)
    assert result.fully_converted_shares_outstanding == 406_448_732
    assert result.fully_converted_equity_nav_usd_per_share == pytest.approx(4.842252)
    assert result.fully_converted_risked_nav_usd_per_share == pytest.approx(3.389580)


def test_calculate_analysis_requires_a_price_for_every_metal() -> None:
    inputs = AnalysisInputs(
        annual_payable_metal_volumes={"silver": 1},
        metal_prices_usd={},
        annual_equivalent_ounces=1,
        aisc_usd_per_equivalent_ounce=1,
        mine_life_years=1,
        shares_outstanding=1,
        share_price_usd=1,
    )

    with pytest.raises(ValueError, match="silver"):
        calculate_analysis(inputs)


def test_consolidate_project_inputs_uses_lifetime_weighted_aisc_and_mine_life() -> None:
    consolidated = consolidate_project_inputs(
        [
            ProjectInputs("Mine A", {"gold": 100}, 100, 1_000, 2, 1_000, 100),
            ProjectInputs("Mine B", {"gold": 300, "silver": 200}, 300, 500, 6, 3_000, 200),
        ]
    )

    assert consolidated.annual_payable_metal_volumes == {"gold": 400, "silver": 200}
    assert consolidated.annual_equivalent_ounces == 400
    assert consolidated.aisc_usd_per_equivalent_ounce == pytest.approx(550)
    assert consolidated.mine_life_years == pytest.approx(5)
    assert consolidated.total_resource_equivalent_ounces == 4_000
    assert consolidated.after_tax_npv_usd == 300
    assert consolidated.partial_total_resource_equivalent_ounces == 4_000
    assert consolidated.partial_after_tax_npv_usd == 300


def test_consolidate_project_inputs_withholds_totals_when_a_project_lacks_them() -> None:
    consolidated = consolidate_project_inputs(
        [
            ProjectInputs("Mine A", {"gold": 100}, 100, 1_000, 2, 1_000, 100),
            ProjectInputs("Mine B", {"gold": 300}, 300, 500, 6),
        ]
    )

    assert consolidated.total_resource_equivalent_ounces is None
    assert consolidated.after_tax_npv_usd is None
    assert consolidated.partial_total_resource_equivalent_ounces == 1_000
    assert consolidated.partial_after_tax_npv_usd == 100
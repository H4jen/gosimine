from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommodityDefinition:
    yahoo_ticker: str
    price_unit: str
    volume_unit_suffix: str
    scenario_decimals: int
    scenario_step: float


COMMODITIES = {
    "gold": CommodityDefinition("GC=F", "USD/oz", "ounces", 0, 100.0),
    "silver": CommodityDefinition("SI=F", "USD/oz", "ounces", 0, 10.0),
    "copper": CommodityDefinition("HG=F", "USD/lb", "pounds", 2, 0.25),
}
from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationSettingDefinition:
    key: str
    label: str
    default_value: str
    choices: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None


BASE_CURRENCY = ApplicationSettingDefinition(
    key="base_currency",
    label="Base currency",
    default_value="SEK",
    choices=("SEK", "USD", "CAD", "AUD", "EUR"),
)


DEFAULT_SCENARIO_GOLD_PRICE = ApplicationSettingDefinition(
    key="default_scenario_gold_price_usd_per_ounce",
    label="Default scenario gold price",
    default_value="6000",
    minimum=0.01,
    maximum=100_000,
    step=100,
)

DEFAULT_SCENARIO_SILVER_PRICE = ApplicationSettingDefinition(
    key="default_scenario_silver_price_usd_per_ounce",
    label="Default scenario silver price",
    default_value="80",
    minimum=0.01,
    maximum=10_000,
    step=10,
)

APPLICATION_SETTINGS = (
    BASE_CURRENCY,
    DEFAULT_SCENARIO_GOLD_PRICE,
    DEFAULT_SCENARIO_SILVER_PRICE,
)
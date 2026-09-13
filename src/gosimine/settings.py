from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationSettingDefinition:
    key: str
    label: str
    default_value: str
    choices: tuple[str, ...]


BASE_CURRENCY = ApplicationSettingDefinition(
    key="base_currency",
    label="Base currency",
    default_value="SEK",
    choices=("SEK", "USD", "CAD", "AUD", "EUR"),
)


APPLICATION_SETTINGS = (BASE_CURRENCY,)
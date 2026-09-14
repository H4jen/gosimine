import json
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).parents[1]
BUILD_SEED_SCRIPT = PROJECT_ROOT / "scripts" / "build_seed.py"


def load_build_seed_module():
    specification = importlib.util.spec_from_file_location("build_seed", BUILD_SEED_SCRIPT)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module
INTAKE_HEADER = (
    "ticker,name,trading_currency,primary_commodity,stage,lifecycle_status,"
    "project_study_as_of_date,project_study_source,resource_as_of_date,resource_source,"
    "financial_as_of_date,financial_source,dilution_as_of_date,dilution_source,"
    "shares_as_of_date,shares_source,annual_production_ounces,aisc_per_ounce,"
    "mine_life_years,basic_shares_outstanding,annual_payable_gold_ounces,"
    "measured_indicated_resource_equivalent_ounces,inferred_resource_equivalent_ounces,"
    "total_resource_equivalent_ounces,after_tax_npv,after_tax_npv_currency,"
    "study_discount_rate_percent,cash,cash_currency,total_debt,total_debt_currency,"
    "potential_conversion_shares,potential_dilution_shares,"
    "study_metal_price_gold_usd_per_ounce\n"
)
INTAKE_ROW = (
    "TSK.V,Talisker Resources,CAD,Gold,Explorer,Explorer,2026-09-14,"
    "https://example.com/study,2026-09-14,https://example.com/resource,"
    "2026-09-14,https://example.com/financial,2026-09-14,"
    "https://example.com/dilution,2026-09-14,https://example.com/shares,"
    "100000,1200,8,100000000,50000,2000000,1000000,3000000,"
    "300000000,CAD,5,100000000,CAD,20000000,CAD,5000000,,2500\n"
)


def test_build_seed_creates_one_json_file_per_intake_row(tmp_path: Path) -> None:
    intake_path = tmp_path / "miner_intake.csv"
    output_directory = tmp_path / "miners"
    intake_path.write_text(
        INTAKE_HEADER + INTAKE_ROW.replace("TSK.V", "tsk.v").replace(",CAD,", ",cad,"),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_SEED_SCRIPT),
            "--intake",
            str(intake_path),
            "--output",
            str(output_directory),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == str(output_directory / "TSK_V.json")
    record = json.loads((output_directory / "TSK_V.json").read_text(encoding="utf-8"))
    assert record | {"parameters": []} == {
        "name": "Talisker Resources",
        "primary_commodity": "Gold",
        "stage": "Explorer",
        "ticker": "TSK.V",
        "trading_currency": "CAD",
        "lifecycle_status": {
            "value": "Explorer",
            "as_of_date": "2026-09-14",
            "source": "https://example.com/study",
        },
        "parameters": [],
    }
    assert {parameter["name"] for parameter in record["parameters"]} == {
        "annual_payable_gold_ounces",
        "annual_production_ounces",
        "aisc_per_ounce",
        "mine_life_years",
        "basic_shares_outstanding",
        "measured_indicated_resource_equivalent_ounces",
        "inferred_resource_equivalent_ounces",
        "total_resource_equivalent_ounces",
        "after_tax_npv_cad",
        "study_discount_rate_percent",
        "cash_cad",
        "total_debt_cad",
        "potential_conversion_shares",
        "study_metal_price_gold_usd_per_ounce",
    }
    parameters = {parameter["name"]: parameter for parameter in record["parameters"]}
    assert parameters["annual_production_ounces"]["source"] == "https://example.com/study"
    assert parameters["total_resource_equivalent_ounces"]["source"] == (
        "https://example.com/resource"
    )
    assert parameters["cash_cad"]["source"] == "https://example.com/financial"
    assert parameters["cash_cad"]["unit"] == "CAD"
    assert parameters["annual_production_ounces"]["unit"] == "AuEq oz/year"
    assert parameters["aisc_per_ounce"]["unit"] == "USD/AuEq oz"
    assert parameters["total_resource_equivalent_ounces"]["unit"] == "AuEq oz"


def test_build_seed_accepts_pound_based_payable_copper(tmp_path: Path) -> None:
    intake_path = tmp_path / "miner_intake.csv"
    output_directory = tmp_path / "miners"
    header = INTAKE_HEADER.removesuffix("\n") + ",annual_payable_copper_pounds,study_metal_price_copper_usd_per_pound\n"
    row = INTAKE_ROW.removesuffix("\n") + ",7000000,4.50\n"
    intake_path.write_text(header + row, encoding="utf-8")

    build_seed = load_build_seed_module()
    build_seed.build_seed(intake_path, output_directory)

    record = json.loads((output_directory / "TSK_V.json").read_text(encoding="utf-8"))
    parameters = {parameter["name"]: parameter for parameter in record["parameters"]}
    assert parameters["annual_payable_copper_pounds"]["unit"] == "Cu lb/year"
    assert parameters["study_metal_price_copper_usd_per_pound"]["unit"] == "USD/lb"


def test_build_seed_skips_an_existing_miner_file(tmp_path: Path) -> None:
    intake_path = tmp_path / "miner_intake.csv"
    output_directory = tmp_path / "miners"
    output_directory.mkdir()
    (output_directory / "TSK_V.json").write_text("{}\n", encoding="utf-8")
    intake_path.write_text(INTAKE_HEADER + INTAKE_ROW, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_SEED_SCRIPT),
            "--intake",
            str(intake_path),
            "--output",
            str(output_directory),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert (output_directory / "TSK_V.json").read_text(encoding="utf-8") == "{}\n"


def test_build_seed_allows_an_explicit_zero_debt_balance(tmp_path: Path) -> None:
    intake_path = tmp_path / "miner_intake.csv"
    output_directory = tmp_path / "miners"
    intake_path.write_text(
        INTAKE_HEADER + INTAKE_ROW.replace("20000000,CAD", "0,CAD"),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(BUILD_SEED_SCRIPT),
            "--intake",
            str(intake_path),
            "--output",
            str(output_directory),
        ],
        check=True,
    )

    record = json.loads((output_directory / "TSK_V.json").read_text(encoding="utf-8"))
    parameters = {parameter["name"]: parameter for parameter in record["parameters"]}
    assert parameters["total_debt_cad"]["value"] == 0


def test_build_seed_rejects_a_row_missing_a_core_analysis_value(tmp_path: Path) -> None:
    intake_path = tmp_path / "miner_intake.csv"
    output_directory = tmp_path / "miners"
    intake_path.write_text(
        INTAKE_HEADER + INTAKE_ROW.replace(",100000,1200,8,100000000,", ",100000,1200,8,,"),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(BUILD_SEED_SCRIPT),
            "--intake",
            str(intake_path),
            "--output",
            str(output_directory),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "basic_shares_outstanding" in result.stderr
    assert not output_directory.exists()


def test_build_seed_allows_a_partial_dossier_with_sourced_shares(tmp_path: Path) -> None:
    intake_path = tmp_path / "miner_intake.csv"
    output_directory = tmp_path / "miners"
    partial_row = INTAKE_ROW.replace("100000,1200,8,100000000,50000", ",,,100000000,")
    intake_path.write_text(INTAKE_HEADER + partial_row, encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(BUILD_SEED_SCRIPT),
            "--intake",
            str(intake_path),
            "--output",
            str(output_directory),
        ],
        check=True,
    )

    record = json.loads((output_directory / "TSK_V.json").read_text(encoding="utf-8"))
    parameters = {parameter["name"]: parameter for parameter in record["parameters"]}
    assert parameters["basic_shares_outstanding"]["value"] == 100000000
    assert "annual_production_ounces" not in parameters
    assert "aisc_per_ounce" not in parameters


def test_build_seed_can_validate_yahoo_listing_data(tmp_path: Path) -> None:
    intake_path = tmp_path / "miner_intake.csv"
    output_directory = tmp_path / "miners"
    intake_path.write_text(INTAKE_HEADER + INTAKE_ROW, encoding="utf-8")

    class FakeYahooFinanceClient:
        def get_quote(self, ticker: str):
            assert ticker == "TSK.V"
            return SimpleNamespace(price=4.10, currency="CAD")

        def get_shares_outstanding(self, ticker: str) -> float:
            assert ticker == "TSK.V"
            return 100_000_000

    build_seed = load_build_seed_module()
    build_seed.build_seed(
        intake_path, output_directory, verify_yahoo=True, yahoo_client=FakeYahooFinanceClient()
    )

    assert (output_directory / "TSK_V.json").exists()


def test_build_seed_rejects_a_yahoo_currency_mismatch(tmp_path: Path) -> None:
    intake_path = tmp_path / "miner_intake.csv"
    output_directory = tmp_path / "miners"
    intake_path.write_text(INTAKE_HEADER + INTAKE_ROW, encoding="utf-8")

    class FakeYahooFinanceClient:
        def get_quote(self, ticker: str):
            return SimpleNamespace(price=4.10, currency="USD")

        def get_shares_outstanding(self, ticker: str) -> float:
            return 100_000_000

    build_seed = load_build_seed_module()
    with __import__("pytest").raises(ValueError, match="currency mismatch"):
        build_seed.build_seed(
            intake_path, output_directory, verify_yahoo=True, yahoo_client=FakeYahooFinanceClient()
        )

    assert not output_directory.exists()


def test_build_seed_marks_blank_sources_as_missing(tmp_path: Path) -> None:
    intake_path = tmp_path / "miner_intake.csv"
    output_directory = tmp_path / "miners"
    intake_path.write_text(
        INTAKE_HEADER + INTAKE_ROW.replace("https://example.com/study", ""),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(BUILD_SEED_SCRIPT),
            "--intake",
            str(intake_path),
            "--output",
            str(output_directory),
        ],
        check=True,
    )

    record = json.loads((output_directory / "TSK_V.json").read_text(encoding="utf-8"))
    assert record["lifecycle_status"]["source"] == "Source missing"
    parameters = {parameter["name"]: parameter for parameter in record["parameters"]}
    assert parameters["annual_production_ounces"]["source"] == "Source missing"


def test_build_seed_marks_blank_optional_dates_with_a_valid_placeholder(tmp_path: Path) -> None:
    intake_path = tmp_path / "miner_intake.csv"
    output_directory = tmp_path / "miners"
    intake_path.write_text(
        INTAKE_HEADER + INTAKE_ROW.replace(",2026-09-14,https://example.com/study,", ",,https://example.com/study,"),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(BUILD_SEED_SCRIPT),
            "--intake",
            str(intake_path),
            "--output",
            str(output_directory),
        ],
        check=True,
    )

    record = json.loads((output_directory / "TSK_V.json").read_text(encoding="utf-8"))
    assert record["lifecycle_status"]["as_of_date"] == "1900-01-01"
    parameters = {parameter["name"]: parameter for parameter in record["parameters"]}
    assert parameters["annual_production_ounces"]["as_of_date"] == "1900-01-01"


def test_build_seed_omits_blank_optional_parameters(tmp_path: Path) -> None:
    intake_path = tmp_path / "miner_intake.csv"
    output_directory = tmp_path / "miners"
    intake_path.write_text(
        INTAKE_HEADER
        + INTAKE_ROW.replace(
            "8,100000000,50000,2000000,1000000,3000000,300000000,CAD,5,"
            "100000000,CAD,20000000,CAD,5000000,,2500",
            ",100000000,50000,,,,,,,,,,,",
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(BUILD_SEED_SCRIPT),
            "--intake",
            str(intake_path),
            "--output",
            str(output_directory),
        ],
        check=True,
    )

    record = json.loads((output_directory / "TSK_V.json").read_text(encoding="utf-8"))
    names = {parameter["name"] for parameter in record["parameters"]}
    assert "mine_life_years" not in names
    assert "after_tax_npv_cad" not in names
    assert "potential_conversion_shares" not in names
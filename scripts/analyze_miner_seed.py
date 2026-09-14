from __future__ import annotations

import argparse
import json
from pathlib import Path

from gosimine.seed_audit import audit_seed_record, full_analysis_missing_inputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report which inputs each Gosimine dashboard metric still requires."
    )
    parser.add_argument("seed", type=Path, help="Path to one miner JSON dossier")
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Also print readiness for each individual dashboard metric.",
    )
    arguments = parser.parse_args()

    record = json.loads(arguments.seed.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("Miner seed must contain a JSON object")

    print(f"{record.get('ticker', arguments.seed.stem)}: {record.get('name', '')}")
    seed_missing, runtime_missing = full_analysis_missing_inputs(record)
    print("Missing seed parameters:")
    print("  none" if not seed_missing else f"  {', '.join(seed_missing)}")
    print("Required runtime market data:")
    print("  none" if not runtime_missing else f"  {', '.join(runtime_missing)}")
    if arguments.metrics:
        print("Metric readiness:")
        for readiness in audit_seed_record(record):
            status = "ready" if readiness.ready else f"missing: {', '.join(readiness.missing)}"
            print(f"  {readiness.metric}: {status}")


if __name__ == "__main__":
    main()
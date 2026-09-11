from pathlib import Path

from gosimine.database import Database


def test_add_and_list_miners(tmp_path: Path) -> None:
    database = Database(tmp_path / "gosimine.sqlite3")

    added = database.add_miner("Aurora Gold", "aug", "Gold", "Producer")

    assert database.list_miners() == [
        type(added)(added.id, "Aurora Gold", "AUG", "Gold", "Producer")
    ]
    database.close()

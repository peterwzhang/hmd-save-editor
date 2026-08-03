import json
from pathlib import Path

CATALOG_PATH = Path(__file__).parent.parent / "data" / "catalog.json"

MIN_EXPECTED_COUNTS = {
    "dude": 45,
    "relic": 374,
    "trinket": 32,
    "food": 8,
    "consumable": 7,
    "enemy": 60,
    "enemy_trait": 41,
    "family": 6,
    "stat": 22,
}


def _load_catalog():
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def test_catalog_file_exists_and_parses():
    catalog = _load_catalog()
    assert isinstance(catalog, dict)
    assert len(catalog) > 0


def test_catalog_entries_have_required_fields():
    catalog = _load_catalog()
    for item_id, entry in catalog.items():
        assert entry["id"] == item_id
        assert entry["kind"]
        assert entry["name"]
        assert "sprite" in entry
        assert "description" in entry


def test_catalog_meets_minimum_counts_per_kind():
    catalog = _load_catalog()
    counts = {}
    for entry in catalog.values():
        counts[entry["kind"]] = counts.get(entry["kind"], 0) + 1
    for kind, floor in MIN_EXPECTED_COUNTS.items():
        assert counts.get(kind, 0) >= floor, f"only {counts.get(kind, 0)} {kind} entries, expected >= {floor}"


def test_fixture_save_ids_resolve_in_catalog(fixtures_dir):
    import json as _json

    run = _json.loads((fixtures_dir / "save_data.json").read_text(encoding="utf-8"))
    catalog = _load_catalog()

    ids = set(run["relics_owned"]) | set(run["trinkets_equipped"])
    ids |= {d["type"] for d in run["dudes"].values()}
    ids |= set(run["roster_order"])

    missing = sorted(i for i in ids if i not in catalog)
    assert missing == []

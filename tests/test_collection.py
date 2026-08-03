import pytest

from hmd_editor.model import collection as collection_model
from hmd_editor.savefile import SaveBundle


def test_star_level_reads_existing_entry(save_dir):
    bundle = SaveBundle.load(save_dir)
    assert collection_model.star_level(bundle, 1, "dentist") == "silver"
    assert collection_model.star_level(bundle, 1, "never_seen") == "none"


def test_set_star_gold_on_undiscovered_creates_full_entry(save_dir):
    bundle = SaveBundle.load(save_dir)
    bundle.global_data["collectible_counts_cached"][2]["needs_refresh"] = False

    collection_model.set_star(bundle, 2, "r_new_relic", "gold")

    entry = bundle.global_data["collectibles_by_tier"][2]["r_new_relic"]
    assert entry["gold_star"] is True
    assert entry["silver_star"] is True  # gold implies silver
    assert entry["rounds_played"] == 0.0
    assert entry["best_round"] == 0.0
    assert bundle.global_data["collectible_counts_cached"][2]["needs_refresh"] is True


def test_set_star_downgrades_from_gold_to_silver(save_dir):
    bundle = SaveBundle.load(save_dir)
    collection_model.set_star(bundle, 1, "dentist", "gold")
    assert collection_model.star_level(bundle, 1, "dentist") == "gold"

    collection_model.set_star(bundle, 1, "dentist", "silver")

    entry = bundle.global_data["collectibles_by_tier"][1]["dentist"]
    assert entry["gold_star"] is False
    assert entry["silver_star"] is True


def test_set_star_none_removes_entry(save_dir):
    bundle = SaveBundle.load(save_dir)
    assert "dentist" in bundle.global_data["collectibles_by_tier"][1]

    collection_model.set_star(bundle, 1, "dentist", "none")

    assert "dentist" not in bundle.global_data["collectibles_by_tier"][1]
    assert collection_model.star_level(bundle, 1, "dentist") == "none"


def test_set_star_preserves_rounds_played_on_existing_entry(save_dir):
    bundle = SaveBundle.load(save_dir)
    collection_model.set_star(bundle, 1, "dentist", "gold")
    entry = bundle.global_data["collectibles_by_tier"][1]["dentist"]
    assert entry["rounds_played"] == 5.0
    assert entry["best_round"] == 10.0


def test_set_star_bulk(save_dir):
    bundle = SaveBundle.load(save_dir)
    collection_model.set_star_bulk(bundle, 1, ["a_new_one", "b_new_one"], "discovered")
    assert collection_model.star_level(bundle, 1, "a_new_one") == "discovered"
    assert collection_model.star_level(bundle, 1, "b_new_one") == "discovered"


def test_set_star_rejects_unknown_level(save_dir):
    bundle = SaveBundle.load(save_dir)
    with pytest.raises(ValueError):
        collection_model.set_star(bundle, 1, "dentist", "platinum")


def test_all_ids(save_dir):
    bundle = SaveBundle.load(save_dir)
    assert collection_model.all_ids(bundle, 1) == {"dentist"}
    assert collection_model.all_ids(bundle, 0) == set()

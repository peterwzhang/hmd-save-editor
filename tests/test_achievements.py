import pytest

from hmd_editor.model import achievements as achievements_model
from hmd_editor.savefile import SaveBundle


def test_set_complete_true_forces_full_progress(save_dir):
    bundle = SaveBundle.load(save_dir)
    achievements_model.set_complete(bundle, "big_pumpers", True)

    entry = bundle.global_data["achievement_progress"]["big_pumpers"]
    assert entry["complete"] is True
    assert entry["progress"] == 1.0


def test_set_complete_false_preserves_progress(save_dir):
    bundle = SaveBundle.load(save_dir)
    achievements_model.set_complete(bundle, "the_g_o_a_t", False)

    entry = bundle.global_data["achievement_progress"]["the_g_o_a_t"]
    assert entry["complete"] is False
    assert entry["progress"] == 1.0  # untouched


def test_set_progress_clamped(save_dir):
    bundle = SaveBundle.load(save_dir)
    achievements_model.set_progress(bundle, "big_pumpers", 5.0)
    assert bundle.global_data["achievement_progress"]["big_pumpers"]["progress"] == 1.0

    achievements_model.set_progress(bundle, "big_pumpers", -3.0)
    assert bundle.global_data["achievement_progress"]["big_pumpers"]["progress"] == 0.0


def test_set_progress_creates_missing_achievement(save_dir):
    bundle = SaveBundle.load(save_dir)
    achievements_model.set_progress(bundle, "brand_new_achievement", 0.5)
    entry = bundle.global_data["achievement_progress"]["brand_new_achievement"]
    assert entry == {"id": "brand_new_achievement", "progress": 0.5, "complete": False}


def test_set_minutes_played(save_dir):
    bundle = SaveBundle.load(save_dir)
    achievements_model.set_minutes_played(bundle, 42)
    assert bundle.global_data["minutes_played"] == 42.0
    assert isinstance(bundle.global_data["minutes_played"], float)


def test_list_best_runs(save_dir):
    bundle = SaveBundle.load(save_dir)
    runs = achievements_model.list_best_runs(bundle)
    assert runs == [("aaaaa", bundle.global_data["best_runs"]["aaaaa"])]


def test_set_best_run_pinned(save_dir):
    bundle = SaveBundle.load(save_dir)
    achievements_model.set_best_run_pinned(bundle, "aaaaa", True)
    assert bundle.global_data["best_runs"]["aaaaa"]["pinned"] is True


def test_set_best_run_field_editable_only(save_dir):
    bundle = SaveBundle.load(save_dir)
    achievements_model.set_best_run_field(bundle, "aaaaa", "best_round", 50)
    assert bundle.global_data["best_runs"]["aaaaa"]["best_round"] == 50.0

    with pytest.raises(ValueError):
        achievements_model.set_best_run_field(bundle, "aaaaa", "items", [])


def test_delete_best_run(save_dir):
    bundle = SaveBundle.load(save_dir)
    achievements_model.delete_best_run(bundle, "aaaaa")
    assert "aaaaa" not in bundle.global_data["best_runs"]


def test_set_best_run_pinned_on_legacy_run_missing_field(save_dir):
    bundle = SaveBundle.load(save_dir)
    del bundle.global_data["best_runs"]["aaaaa"]["pinned"]  # simulate an old-format run

    achievements_model.set_best_run_pinned(bundle, "aaaaa", True)

    assert bundle.global_data["best_runs"]["aaaaa"]["pinned"] is True


def test_set_best_run_field_on_legacy_run_missing_field(save_dir):
    bundle = SaveBundle.load(save_dir)
    del bundle.global_data["best_runs"]["aaaaa"]["money_earned"]  # simulate an old-format run

    achievements_model.set_best_run_field(bundle, "aaaaa", "money_earned", 42)

    assert bundle.global_data["best_runs"]["aaaaa"]["money_earned"] == 42.0
    assert isinstance(bundle.global_data["best_runs"]["aaaaa"]["money_earned"], float)

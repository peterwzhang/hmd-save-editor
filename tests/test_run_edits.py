import pytest

from hmd_editor.model import run as run_model
from hmd_editor.savefile import SaveBundle


def test_add_relic_keeps_all_three_lists_in_sync(save_dir):
    bundle = SaveBundle.load(save_dir)
    run_model.add_relic(bundle, "r_new_thing")

    data = bundle.run_data
    assert data["relics_owned"]["r_new_thing"] is True
    assert "r_new_thing" in data["relic_order"]
    assert {"id": "r_new_thing", "type": "relic"} in data["item_acquisition_order"]
    assert run_model.validate(bundle) == []


def test_add_relic_is_idempotent(save_dir):
    bundle = SaveBundle.load(save_dir)
    run_model.add_relic(bundle, "r_bandage")  # already owned in fixture
    assert bundle.run_data["relic_order"].count("r_bandage") == 1
    assert len(
        [i for i in bundle.run_data["item_acquisition_order"] if i["id"] == "r_bandage"]
    ) == 1


def test_remove_relic_does_not_touch_trinkets(save_dir):
    bundle = SaveBundle.load(save_dir)
    # tr_rocket_pants is equipped (not "owned" as a relic) in the fixture;
    # trinkets never appear in relics_owned, so removing a same-named relic
    # (which doesn't exist here) must not be confused with unequipping it.
    run_model.remove_relic(bundle, "tr_rocket_pants")

    data = bundle.run_data
    assert data["trinkets_equipped"]["tr_rocket_pants"] == "warlock"
    assert run_model.validate(bundle) == []


def test_equip_trinket_requires_roster_membership(save_dir):
    bundle = SaveBundle.load(save_dir)
    with pytest.raises(ValueError):
        run_model.equip_trinket(bundle, "tr_bongos", "zombie")  # not on roster


def test_equip_trinket_does_not_touch_relics_owned(save_dir):
    bundle = SaveBundle.load(save_dir)
    run_model.equip_trinket(bundle, "tr_bongos", "dentist")

    data = bundle.run_data
    assert data["trinkets_equipped"]["tr_bongos"] == "dentist"
    assert "tr_bongos" not in data["relics_owned"]
    assert "tr_bongos" not in data["relic_order"]
    assert run_model.validate(bundle) == []


def test_unequip_trinket_discards_it_entirely(save_dir):
    bundle = SaveBundle.load(save_dir)
    run_model.unequip_trinket(bundle, "tr_rocket_pants")
    assert "tr_rocket_pants" not in bundle.run_data["trinkets_equipped"]


def test_add_dude_generates_unique_ids_and_updates_roster(save_dir):
    bundle = SaveBundle.load(save_dir)
    existing = set(bundle.run_data["dudes"])

    new_ids = run_model.add_dude(bundle, "zombie", count=3)

    assert len(new_ids) == 3
    assert len(set(new_ids)) == 3
    assert not (set(new_ids) & existing)
    for unit_id in new_ids:
        dude = bundle.run_data["dudes"][unit_id]
        assert dude == {"type": "zombie", "hp_percent": 1.0, "knockout_rounds": 0.0}
    assert "zombie" in bundle.run_data["roster_order"]


def test_heal_all_restores_full_hp(save_dir):
    bundle = SaveBundle.load(save_dir)
    bundle.run_data["dudes"]["aaa"]["hp_percent"] = 0.1
    bundle.run_data["dudes"]["aaa"]["knockout_rounds"] = 4.0

    run_model.heal_all(bundle)

    for dude in bundle.run_data["dudes"].values():
        assert dude["hp_percent"] == 1.0
        assert dude["knockout_rounds"] == 0.0


def test_set_cash_serializes_as_float(save_dir):
    bundle = SaveBundle.load(save_dir)
    run_model.set_cash(bundle, 5)  # int in
    assert bundle.run_data["cash"] == 5.0
    written = bundle.save()
    assert written == ["save_data.json"]
    assert '"cash":5.0' in (save_dir / "save_data.json").read_text(encoding="utf-8")


def test_set_game_mode(save_dir):
    bundle = SaveBundle.load(save_dir)
    run_model.set_game_mode(bundle, "daily_challenge")
    assert bundle.run_data["game_mode"] == "daily_challenge"


def test_set_consumable_new_and_existing(save_dir):
    bundle = SaveBundle.load(save_dir)
    run_model.set_consumable(bundle, "dude_juice", 9)  # already owned (float)
    assert bundle.run_data["consumables_owned"]["dude_juice"] == 9.0
    assert isinstance(bundle.run_data["consumables_owned"]["dude_juice"], float)

    run_model.set_consumable(bundle, "meteor", 2)  # brand new
    assert bundle.run_data["consumables_owned"]["meteor"] == 2.0
    assert isinstance(bundle.run_data["consumables_owned"]["meteor"], float)


def test_validate_reports_roster_mismatch(save_dir):
    bundle = SaveBundle.load(save_dir)
    bundle.run_data["dudes"]["ccc"] = {
        "type": "ghost",
        "hp_percent": 1.0,
        "knockout_rounds": 0.0,
    }
    warnings = run_model.validate(bundle)
    assert any("ghost" in w for w in warnings)


def test_heal_type_only_heals_that_type(save_dir):
    bundle = SaveBundle.load(save_dir)
    bundle.run_data["dudes"]["aaa"]["hp_percent"] = 0.1  # dentist
    bundle.run_data["dudes"]["bbb"]["hp_percent"] = 0.2  # warlock

    run_model.heal_type(bundle, "dentist")

    assert bundle.run_data["dudes"]["aaa"]["hp_percent"] == 1.0
    assert bundle.run_data["dudes"]["bbb"]["hp_percent"] == 0.2


def test_roster_summary_counts_and_averages(save_dir):
    bundle = SaveBundle.load(save_dir)
    bundle.run_data["dudes"]["aaa"]["hp_percent"] = 0.5
    bundle.run_data["dudes"]["bbb"]["hp_percent"] = 1.0

    summary = run_model.roster_summary(bundle)

    assert summary["dentist"] == {"count": 1, "avg_hp_percent": 0.5}
    assert summary["warlock"] == {"count": 1, "avg_hp_percent": 1.0}


def test_roster_summary_includes_zero_count_roster_types(save_dir):
    bundle = SaveBundle.load(save_dir)
    bundle.run_data["roster_order"].append("zombie")

    summary = run_model.roster_summary(bundle)

    assert summary["zombie"] == {"count": 0, "avg_hp_percent": 1.0}


def test_add_food_and_remove_food(save_dir):
    bundle = SaveBundle.load(save_dir)
    food_id = run_model.add_food(bundle, "ft_baguette", "damage", "dentist")

    assert bundle.run_data["food"][food_id] == {
        "id": food_id,
        "type": "ft_baguette",
        "secondary_stat": "damage",
        "dude_type": "dentist",
    }

    run_model.remove_food(bundle, food_id)
    assert food_id not in bundle.run_data["food"]


def test_add_food_requires_roster_membership(save_dir):
    bundle = SaveBundle.load(save_dir)
    with pytest.raises(ValueError):
        run_model.add_food(bundle, "ft_baguette", "damage", "zombie")

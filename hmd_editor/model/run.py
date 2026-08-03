"""Invariant-preserving edits to the current run (save_data.json).

Several fields in save_data.json describe the same underlying facts from
different angles - ``relics_owned``, ``relic_order``, and
``item_acquisition_order`` all track the same set of owned *relics* - and
nothing in the game appears to re-derive one from another on load. A naive
edit that touches only one of them (e.g. adding a key to ``relics_owned`` but
not ``relic_order``) produces a save the game may not read back correctly.
Every mutation here keeps all of them in sync; callers should not poke
``bundle.run_data`` directly for anything modeled below.

Trinkets are a separate concept from relics despite sharing the same catalog
id namespace (``tr_*``): a trinket has no independent "owned" state at all.
``trinkets_equipped`` (id -> dude type) is the sole record of it - equipping
one *is* acquiring it, and unequipping it discards it entirely. Real save
data confirms trinket ids never appear in ``relics_owned``/``relic_order``.
"""

from __future__ import annotations

import random
import string

from ..savefile import SaveBundle

FILE = "save_data.json"

_ID_ALPHABET = string.ascii_lowercase + string.digits


def _new_unit_id(existing: set) -> str:
    for length in (3, 4, 5):
        for _ in range(200):
            candidate = "".join(random.choices(_ID_ALPHABET, k=length))
            if candidate not in existing:
                return candidate
    raise RuntimeError("could not generate a unique dude id")


def add_relic(bundle: SaveBundle, relic_id: str) -> None:
    run = bundle.run_data
    if relic_id in run["relics_owned"]:
        return
    run["relics_owned"][relic_id] = True
    run["relic_order"].append(relic_id)
    run["item_acquisition_order"].append({"id": relic_id, "type": "relic"})


def remove_relic(bundle: SaveBundle, relic_id: str) -> None:
    run = bundle.run_data
    if relic_id not in run["relics_owned"]:
        return
    del run["relics_owned"][relic_id]
    run["relic_order"] = [r for r in run["relic_order"] if r != relic_id]
    run["item_acquisition_order"] = [
        item
        for item in run["item_acquisition_order"]
        if not (item.get("type") == "relic" and item.get("id") == relic_id)
    ]


def equip_trinket(bundle: SaveBundle, trinket_id: str, dude_type: str) -> None:
    """Equip (and thereby acquire) a trinket for a roster dude. Trinkets are
    not relics: this does not touch relics_owned/relic_order."""
    run = bundle.run_data
    if dude_type not in run["roster_order"]:
        raise ValueError(f"{dude_type!r} is not on the current roster")
    run["trinkets_equipped"][trinket_id] = dude_type


def unequip_trinket(bundle: SaveBundle, trinket_id: str) -> None:
    """Unequip a trinket. Since equipping is the only form of ownership a
    trinket has, this discards it entirely rather than returning it to some
    unequipped inventory (there isn't one)."""
    bundle.run_data["trinkets_equipped"].pop(trinket_id, None)


def add_dude(bundle: SaveBundle, dude_type: str, count: int = 1) -> list:
    run = bundle.run_data
    existing_ids = set(run["dudes"])
    new_ids = []
    for _ in range(count):
        unit_id = _new_unit_id(existing_ids)
        existing_ids.add(unit_id)
        run["dudes"][unit_id] = {
            "type": dude_type,
            "hp_percent": 1.0,
            "knockout_rounds": 0.0,
        }
        new_ids.append(unit_id)
    if dude_type not in run["roster_order"]:
        run["roster_order"].append(dude_type)
    return new_ids


def remove_dude(bundle: SaveBundle, unit_id: str) -> None:
    bundle.run_data["dudes"].pop(unit_id, None)


def heal_all(bundle: SaveBundle) -> None:
    for dude in bundle.run_data["dudes"].values():
        dude["hp_percent"] = 1.0
        dude["knockout_rounds"] = 0.0


def heal_type(bundle: SaveBundle, dude_type: str) -> None:
    for dude in bundle.run_data["dudes"].values():
        if dude["type"] == dude_type:
            dude["hp_percent"] = 1.0
            dude["knockout_rounds"] = 0.0


def roster_summary(bundle: SaveBundle) -> dict:
    """Per-type unit count and average HP percent, for the roster overview.
    Types on `roster_order` with zero surviving units still appear, at 0
    count and 100% HP, so the UI has something sane to show."""
    run = bundle.run_data
    summary = {t: {"count": 0, "avg_hp_percent": 1.0} for t in run["roster_order"]}
    totals: dict = {}
    for dude in run["dudes"].values():
        dtype = dude["type"]
        totals.setdefault(dtype, []).append(dude["hp_percent"])
    for dtype, hp_values in totals.items():
        summary.setdefault(dtype, {"count": 0, "avg_hp_percent": 1.0})
        summary[dtype]["count"] = len(hp_values)
        summary[dtype]["avg_hp_percent"] = sum(hp_values) / len(hp_values)
    return summary


def add_food(bundle: SaveBundle, food_type: str, secondary_stat: str, dude_type: str) -> str:
    run = bundle.run_data
    if dude_type not in run["roster_order"]:
        raise ValueError(f"{dude_type!r} is not on the current roster")
    existing_ids = set(run["food"])
    food_id = _new_unit_id(existing_ids)
    run["food"][food_id] = {
        "id": food_id,
        "type": food_type,
        "secondary_stat": secondary_stat,
        "dude_type": dude_type,
    }
    return food_id


def remove_food(bundle: SaveBundle, food_id: str) -> None:
    bundle.run_data["food"].pop(food_id, None)


def set_consumable(bundle: SaveBundle, consumable_id: str, count) -> None:
    run = bundle.run_data
    if consumable_id in run["consumables_owned"]:
        bundle.set_value(FILE, ["consumables_owned", consumable_id], count)
    else:
        run["consumables_owned"][consumable_id] = float(count)


def set_cash(bundle: SaveBundle, value) -> None:
    bundle.set_value(FILE, ["cash"], value)


def set_week(bundle: SaveBundle, value) -> None:
    bundle.set_value(FILE, ["week"], value)


def set_rank(bundle: SaveBundle, value) -> None:
    bundle.set_value(FILE, ["rank"], value)


def set_game_mode(bundle: SaveBundle, value: str) -> None:
    bundle.set_value(FILE, ["game_mode"], value)


def validate(bundle: SaveBundle) -> list:
    """Return a list of human-readable warnings about internal
    inconsistencies in the run data. An empty list means everything the
    editor knows to check looks consistent."""
    warnings = []
    run = bundle.run_data

    if set(run["relics_owned"]) != set(run["relic_order"]):
        warnings.append("relics_owned and relic_order disagree on the owned relic set")
    if len(run["relic_order"]) != len(set(run["relic_order"])):
        warnings.append("relic_order has duplicate entries")

    for tr_id, dude_type in run["trinkets_equipped"].items():
        if dude_type not in run["roster_order"]:
            warnings.append(
                f"trinket {tr_id!r} is equipped to {dude_type!r}, which is not on the roster"
            )

    dude_types_in_use = {d["type"] for d in run["dudes"].values()}
    for dtype in dude_types_in_use:
        if dtype not in run["roster_order"]:
            warnings.append(f"dude type {dtype!r} has units but is not in roster_order")

    return warnings

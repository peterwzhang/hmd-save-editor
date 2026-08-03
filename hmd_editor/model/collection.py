"""Collection (Dudex) discovery and star editing, over global.json.

``collectibles_by_tier[tier]`` is a sparse dict: a collectible only gets an
entry once it has been discovered at that tier. ``gold_star`` implies
``silver_star`` implies presence in the dict; this module enforces that
whenever a star level is set, rather than leaving the two booleans free to
disagree with each other or with a missing entry.

Any edit here must also flip
``collectible_counts_cached[tier]["needs_refresh"]`` so the game recomputes
cached totals instead of showing stale numbers.
"""

from __future__ import annotations

FILE = "global.json"

LEVELS = ("none", "discovered", "silver", "gold")


def _tier_dict(bundle, tier: int) -> dict:
    return bundle.global_data["collectibles_by_tier"][tier]


def star_level(bundle, tier: int, item_id: str) -> str:
    entry = _tier_dict(bundle, tier).get(item_id)
    if entry is None:
        return "none"
    if entry.get("gold_star"):
        return "gold"
    if entry.get("silver_star"):
        return "silver"
    return "discovered"


def set_star(bundle, tier: int, item_id: str, level: str) -> None:
    """Set the exact star level for `item_id` at `tier`. Setting "none"
    removes the entry entirely (un-discovers it); any other level creates
    the entry if needed and sets both star flags to match exactly (so
    setting "silver" on a gold item downgrades it, it does not merely
    raise the floor)."""
    if level not in LEVELS:
        raise ValueError(f"unknown star level {level!r}, expected one of {LEVELS}")

    tier_dict = _tier_dict(bundle, tier)

    if level == "none":
        tier_dict.pop(item_id, None)
    else:
        entry = tier_dict.get(item_id)
        if entry is None:
            entry = {
                "id": item_id,
                "gold_star": False,
                "silver_star": False,
                "rounds_played": 0.0,
                "best_round": 0.0,
            }
            tier_dict[item_id] = entry
        entry["silver_star"] = level in ("silver", "gold")
        entry["gold_star"] = level == "gold"

    _mark_needs_refresh(bundle, tier)


def set_star_bulk(bundle, tier: int, item_ids, level: str) -> None:
    for item_id in item_ids:
        set_star(bundle, tier, item_id, level)


def all_ids(bundle, tier: int) -> set:
    """All discovered ids at a tier."""
    return set(_tier_dict(bundle, tier))


def _mark_needs_refresh(bundle, tier: int) -> None:
    bundle.global_data["collectible_counts_cached"][tier]["needs_refresh"] = True

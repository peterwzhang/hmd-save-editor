"""Achievement, playtime, and best-run editing over global.json."""

from __future__ import annotations

FILE = "global.json"

_EDITABLE_BEST_RUN_FIELDS = ("money_earned", "money_spent", "best_round", "rank")


def set_complete(bundle, achievement_id: str, complete: bool) -> None:
    """Toggle an achievement's complete flag. Marking it complete also sets
    progress to 1.0, matching what completing it in-game would leave behind;
    clearing it leaves progress untouched so partial progress isn't lost."""
    entry = _get_or_create(bundle, achievement_id)
    entry["complete"] = bool(complete)
    if complete:
        entry["progress"] = 1.0


def set_progress(bundle, achievement_id: str, progress: float) -> None:
    entry = _get_or_create(bundle, achievement_id)
    entry["progress"] = max(0.0, min(1.0, float(progress)))


def _get_or_create(bundle, achievement_id: str) -> dict:
    achievements = bundle.global_data["achievement_progress"]
    entry = achievements.get(achievement_id)
    if entry is None:
        entry = {"id": achievement_id, "progress": 0.0, "complete": False}
        achievements[achievement_id] = entry
    return entry


def set_minutes_played(bundle, minutes) -> None:
    bundle.set_value(FILE, ["minutes_played"], minutes)


def list_best_runs(bundle) -> list:
    return list(bundle.global_data["best_runs"].items())


def set_best_run_pinned(bundle, run_id: str, pinned: bool) -> None:
    # Runs saved by older game versions may not have a "pinned" field at
    # all; bundle.set_value() needs an existing value to coerce the type
    # against, so fall back to inserting it directly.
    run = bundle.global_data["best_runs"][run_id]
    if "pinned" in run:
        bundle.set_value(FILE, ["best_runs", run_id, "pinned"], pinned)
    else:
        run["pinned"] = bool(pinned)


def set_best_run_field(bundle, run_id: str, field: str, value) -> None:
    if field not in _EDITABLE_BEST_RUN_FIELDS:
        raise ValueError(f"editing {field!r} on a best run is not supported")
    # As above: money_earned/money_spent in particular are missing on runs
    # saved before the game tracked them.
    run = bundle.global_data["best_runs"][run_id]
    if field in run:
        bundle.set_value(FILE, ["best_runs", run_id, field], value)
    else:
        run[field] = float(value)


def delete_best_run(bundle, run_id: str) -> None:
    bundle.global_data["best_runs"].pop(run_id, None)

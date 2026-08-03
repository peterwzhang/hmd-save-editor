"""Loading, dirty-tracking, and safe atomic saving of an HMD save folder."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import jsonio

FILENAMES = ("global.json", "save_data.json", "settings.json")

MAX_BACKUPS_PER_FILE = 20


@dataclass
class _LoadedFile:
    path: Path
    data: object
    original_text: str


class SaveBundle:
    """The three save files from one HMD save folder, loaded and dirty-tracked.

    Any subset of the three files may be present; missing files are simply
    absent from the bundle so callers (and the UI) can disable the parts that
    depend on them.
    """

    def __init__(self):
        self.directory: Optional[Path] = None
        self._files: dict[str, _LoadedFile] = {}

    @classmethod
    def load(cls, directory) -> "SaveBundle":
        directory = Path(directory)
        bundle = cls()
        bundle.directory = directory
        for name in FILENAMES:
            path = directory / name
            if not path.is_file():
                continue
            raw = path.read_text(encoding="utf-8")
            data = jsonio.loads(raw)
            bundle._files[name] = _LoadedFile(path=path, data=data, original_text=raw)
        if not bundle._files:
            raise FileNotFoundError(
                f"No HMD save files ({', '.join(FILENAMES)}) found in {directory}"
            )
        return bundle

    def has(self, name: str) -> bool:
        return name in self._files

    def data(self, name: str):
        f = self._files.get(name)
        return f.data if f else None

    @property
    def global_data(self):
        return self.data("global.json")

    @property
    def run_data(self):
        return self.data("save_data.json")

    @property
    def settings_data(self):
        return self.data("settings.json")

    def is_dirty(self, name: Optional[str] = None) -> bool:
        names = [name] if name else list(self._files)
        for n in names:
            f = self._files.get(n)
            if f is not None and jsonio.dumps(f.data) != f.original_text:
                return True
        return False

    def dirty_files(self) -> list[str]:
        return [n for n in self._files if self.is_dirty(n)]

    def revert(self, name: Optional[str] = None) -> None:
        """Discard in-memory edits, restoring the data as it was on load (or
        as of the last successful save)."""
        names = [name] if name else list(self._files)
        for n in names:
            f = self._files.get(n)
            if f is not None:
                f.data = jsonio.loads(f.original_text)

    def set_value(self, name: str, path: list, value) -> None:
        """Set a value inside file `name`'s data at `path` (a list of dict
        keys / list indices to walk down to the parent container).

        The new value's numeric type is coerced to match whatever it
        replaces: GameMaker writes almost every number as a float, so writing
        a bare Python ``int`` where a float belongs would turn ``"150.0"``
        into ``"150"``, a textual change the game does not make itself.
        """
        f = self._files.get(name)
        if f is None:
            raise KeyError(f"{name} is not loaded")
        container = f.data
        for key in path[:-1]:
            container = container[key]
        last = path[-1]
        container[last] = _coerce_like(container[last], value)

    def save(self, backup: bool = True) -> list[str]:
        """Write every changed file back to disk, in place, atomically.
        Returns the list of filenames actually written; unchanged files are
        left untouched entirely (not even their mtime changes)."""
        if self.directory is None:
            raise RuntimeError("SaveBundle has no directory to save to")
        written = []
        for name in self.dirty_files():
            f = self._files[name]
            new_text = jsonio.dumps(f.data)
            if backup:
                _write_backup(self.directory, f.path, f.original_text)
            tmp_path = f.path.with_suffix(f.path.suffix + ".tmp")
            tmp_path.write_text(new_text, encoding="utf-8")
            os.replace(tmp_path, f.path)
            f.original_text = new_text
            written.append(name)
        return written


def _coerce_like(old, new):
    if isinstance(old, bool):
        return bool(new)
    if isinstance(old, float):
        return float(new)
    if isinstance(old, int):
        return int(new)
    return new


def _write_backup(directory: Path, path: Path, original_text: str) -> None:
    backup_dir = directory / "hmd_editor_backups"
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_dir / f"{path.name}.{stamp}.json"
    backup_path.write_text(original_text, encoding="utf-8")
    _prune_backups(backup_dir, path.name)


def _prune_backups(backup_dir: Path, filename: str) -> None:
    matches = sorted(backup_dir.glob(f"{filename}.*.json"))
    excess = len(matches) - MAX_BACKUPS_PER_FILE
    if excess > 0:
        for old in matches[:excess]:
            old.unlink(missing_ok=True)

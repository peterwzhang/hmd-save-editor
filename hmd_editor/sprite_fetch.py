"""Downloads sprite images referenced by the catalog into cache/sprites/.

Shared by tools/fetch_catalog.py (maintainer catalog regeneration) and the
app's own first-run icon fetch (hmd_editor/ui/sprite_download.py), so the
network/retry logic lives in one place. Pure stdlib - no PySide6 import - so
it stays usable from the standalone tools/ script and easily unit-testable.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Iterable, Optional

BASE_URL = "https://howmanydudes.com"
USER_AGENT = "Mozilla/5.0 (compatible; hmd-save-editor-catalog-fetch/1.0)"
REQUEST_DELAY_SECONDS = 0.3


def missing_sprite_paths(sprite_urls: Iterable[str], sprites_dir: Path) -> list[str]:
    """Sprite URL paths (e.g. "/sprites/foo.webp") not already cached locally."""
    return [p for p in sprite_urls if not (sprites_dir / Path(p).name).is_file()]


def download_sprites(
    sprite_paths: Iterable[str],
    sprites_dir: Path,
    *,
    on_progress: Optional[Callable[[int, int], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> list[str]:
    """Downloads each sprite path into sprites_dir, skipping ones already on
    disk. Returns the sprite paths that failed to download.

    `on_progress(done, total)` is called after each attempt, if given.
    `should_cancel()` is polled before each download, if given.
    """
    sprites_dir.mkdir(parents=True, exist_ok=True)
    sprite_paths = list(sprite_paths)
    failed: list[str] = []
    for i, sprite_path in enumerate(sprite_paths):
        if should_cancel is not None and should_cancel():
            break
        dest = sprites_dir / Path(sprite_path).name
        if not dest.exists():
            if i > 0:
                time.sleep(REQUEST_DELAY_SECONDS)
            try:
                req = urllib.request.Request(
                    BASE_URL + sprite_path, headers={"User-Agent": USER_AGENT}
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    dest.write_bytes(resp.read())
            except urllib.error.URLError:
                failed.append(sprite_path)
        if on_progress is not None:
            on_progress(i + 1, len(sprite_paths))
    return failed

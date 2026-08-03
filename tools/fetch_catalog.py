#!/usr/bin/env python3
"""Scrape https://howmanydudes.com/en/dudex for display names, descriptions,
and sprite paths, and write data/catalog.json.

The wiki is a server-prerendered SvelteKit site: each listing page
(/en/dudex/<kind>) contains one <article data-kind="<kind>"> per entry, with
an icon <img>, a name (and for dudes, an ability name), and a description.
This is plain stdlib html.parser - no BeautifulSoup, no JS execution needed.

Usage:
    python tools/fetch_catalog.py             # writes data/catalog.json
    python tools/fetch_catalog.py --sprites   # also downloads cache/sprites/*.webp
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE_URL = "https://howmanydudes.com"
LISTING_KINDS = (
    "dude",
    "relic",
    "trinket",
    "food",
    "consumable",
    "enemy",
    "enemy_trait",
    "family",
    "stat",
)
# Sanity floor per kind, from a known-good scrape. Real counts only grow as
# the game adds content; a big drop means the page structure broke, not that
# content was removed.
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

USER_AGENT = "Mozilla/5.0 (compatible; hmd-save-editor-catalog-fetch/1.0)"
REQUEST_DELAY_SECONDS = 0.3

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "data" / "catalog.json"
SPRITES_DIR = REPO_ROOT / "cache" / "sprites"


class DudexPageParser(HTMLParser):
    """Extracts one record per <article data-kind="..."> block on a
    /en/dudex/<kind> listing page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.entries: list[dict] = []
        self._article_depth = 0
        self._current: dict | None = None
        self._field: str | None = None
        self._field_p_depth = 0
        self._header_buf: list[str] = []
        self._desc_buf: list[str] = []

    def handle_starttag(self, tag, attrs_list):
        attrs = dict(attrs_list)
        if tag == "article" and "data-kind" in attrs:
            self._article_depth += 1
            self._current = {"kind": attrs["data-kind"], "id": None, "sprite": None}
            self._header_buf = []
            self._desc_buf = []
            self._field = None
            self._field_p_depth = 0
            return
        if self._article_depth == 0:
            return
        if tag == "article":
            self._article_depth += 1
            return

        cur = self._current
        if cur is not None:
            if cur["id"] is None and tag == "a" and "href" in attrs:
                href = attrs["href"]
                if href.startswith("/en/dudex/"):
                    cur["id"] = href.rsplit("/", 1)[-1]
            if cur["sprite"] is None and tag == "img" and "src" in attrs:
                src = attrs["src"]
                if src.startswith("/sprites/"):
                    cur["sprite"] = src

        classes = attrs.get("class", "").split()
        if tag == "p" and "header" in classes and "name" in classes:
            self._field = "header"
            self._field_p_depth = 1
        elif tag == "p" and "description" in classes:
            self._field = "desc"
            self._field_p_depth = 1
        elif self._field is not None and tag == "p":
            self._field_p_depth += 1

    def handle_endtag(self, tag):
        if self._article_depth == 0:
            return
        if tag == "p" and self._field is not None:
            self._field_p_depth -= 1
            if self._field_p_depth == 0:
                if self._field == "header":
                    self._finish_header("".join(self._header_buf))
                elif self._field == "desc":
                    self._current["description"] = " ".join(
                        "".join(self._desc_buf).split()
                    )
                self._field = None
        if tag == "article":
            self._article_depth -= 1
            if self._article_depth == 0 and self._current is not None:
                self.entries.append(self._current)
                self._current = None

    def handle_data(self, data):
        if self._field == "header":
            self._header_buf.append(data)
        elif self._field == "desc":
            self._desc_buf.append(data)

    def _finish_header(self, text):
        text = " ".join(text.split())
        if "›" in text:  # '›'
            name, _, ability = text.partition("›")
            self._current["name"] = name.strip()
            self._current["ability_name"] = ability.strip() or None
        else:
            self._current["name"] = text.strip()
            self._current["ability_name"] = None


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def fetch_catalog() -> dict[str, dict]:
    catalog: dict[str, dict] = {}
    for i, kind in enumerate(LISTING_KINDS):
        if i > 0:
            time.sleep(REQUEST_DELAY_SECONDS)
        url = f"{BASE_URL}/en/dudex/{kind}"
        print(f"fetching {url}", file=sys.stderr)
        html = fetch(url)

        parser = DudexPageParser()
        parser.feed(html)
        entries = parser.entries

        floor = MIN_EXPECTED_COUNTS[kind]
        if len(entries) < floor:
            raise RuntimeError(
                f"{kind}: only found {len(entries)} entries, expected at least "
                f"{floor}. The wiki's page structure may have changed - the "
                f"parser in this script needs updating."
            )

        missing = [e for e in entries if not e.get("id") or not e.get("name")]
        if missing:
            raise RuntimeError(
                f"{kind}: {len(missing)} entries missing id or name: {missing[:3]}"
            )

        for entry in entries:
            catalog[entry["id"]] = {
                "id": entry["id"],
                "kind": entry["kind"],
                "name": entry["name"],
                "ability_name": entry.get("ability_name"),
                "description": entry.get("description") or "",
                "sprite": entry["sprite"],
            }
        print(f"  {kind}: {len(entries)} entries", file=sys.stderr)

    return catalog


def download_sprites(catalog: dict[str, dict]) -> None:
    SPRITES_DIR.mkdir(parents=True, exist_ok=True)
    sprites = sorted({e["sprite"] for e in catalog.values() if e["sprite"]})
    print(f"downloading {len(sprites)} sprites...", file=sys.stderr)
    for i, sprite_path in enumerate(sprites):
        dest = SPRITES_DIR / Path(sprite_path).name
        if dest.exists():
            continue
        if i > 0:
            time.sleep(REQUEST_DELAY_SECONDS)
        url = BASE_URL + sprite_path
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                dest.write_bytes(resp.read())
        except urllib.error.HTTPError as e:
            print(f"  warning: failed to fetch {url}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sprites", action="store_true", help="also download sprite images"
    )
    args = parser.parse_args()

    catalog = fetch_catalog()

    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CATALOG_PATH.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {len(catalog)} entries to {CATALOG_PATH}", file=sys.stderr)

    if args.sprites:
        download_sprites(catalog)


if __name__ == "__main__":
    main()

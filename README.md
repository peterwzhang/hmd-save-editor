# HMD Save Editor

A desktop save editor for *How Many Dudes?* (Butterscotch Shenanigans).

This is an unofficial fan-made tool and is not affiliated with or endorsed by Butterscotch Shenanigans.

Edit your current run, your permanent collection (discovered / silver / gold stars), and your achievements.

## Installing

Requires [uv](https://docs.astral.sh/uv/).

```
uv sync
```

## Running

```
uv run python -m hmd_editor
```

(equivalently, `uv run hmd-save-editor`)

On launch, use **Open save folder...** (or drag a folder or a save file onto the window) to load your save.
Nothing is auto-detected: you choose which files to open.

The first time you run the editor, it'll ask permission to download item icons from [howmanydudes.com](https://howmanydudes.com) (a fan wiki) into a local `cache/sprites/` folder.
This only happens once, and only if you say yes; decline and items just show with a placeholder instead.

## Where the game keeps its save files

- **Windows**: `%LOCALAPPDATA%\HowManyDudes\<steam_id>\Game\`
  containing `global.json`, `save_data.json`, and `settings.json`.
  The game also keeps its own rotating copy under `%LOCALAPPDATA%\HowManyDudes\Backup\<steam_id>\Game\`, which can be useful if a run gets corrupted.

If you're on WSL, that path is reachable at `/mnt/c/Users/<you>/AppData/Local/HowManyDudes/...`.

### Running the editor itself on WSL

WSLg's Wayland compositor has a popup-positioning bug: dropdown lists can get stranded on screen after you move the window.
The editor works around this automatically by preferring X11 over Wayland when it detects WSL, but that needs a few extra system libraries:

```
sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 libxcb-xkb1
```

Without them, dropdowns fall back to the buggy default (Wayland) rather than failing to start.

## Important: Steam Cloud

If Steam is running with cloud sync enabled, it can overwrite an edited save.
Recommended workflow:

1. Close *How Many Dudes?* and quit Steam.
2. Copy the `Game` folder somewhere else (e.g. your Desktop).
3. Open the copy in this editor, make your edits, save.
4. Copy the edited files back over the originals.
5. Start Steam and the game.

## What gets edited

- `save_data.json` - the active run: cash, week, rank, roster, relics, trinkets, consumables, food.
- `global.json` - permanent progress: collection discovery/star state, achievements, best runs.
- `settings.json` - not editable; passed through unchanged.

Every save creates a timestamped backup of any file it changes, in a `hmd_editor_backups/` folder next to your save files, so you can always roll back.

## Rebuilding the item catalog

The display names, descriptions, and icons shown in the editor come from a catalog scraped from [howmanydudes.com/en/dudex](https://howmanydudes.com/en/dudex).
A pre-built copy is committed at `data/catalog.json`. To regenerate it (e.g. after a game update adds new items):

```
uv run python tools/fetch_catalog.py --sprites
```

## Running the tests

```
uv run pytest
```

## License

[MIT](LICENSE)

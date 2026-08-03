import time

from hmd_editor.savefile import SaveBundle


def test_load_finds_all_three_files(save_dir):
    bundle = SaveBundle.load(save_dir)
    assert bundle.has("global.json")
    assert bundle.has("save_data.json")
    assert bundle.has("settings.json")
    assert bundle.run_data["cash"] == 150.0


def test_load_tolerates_missing_files(tmp_path, save_dir):
    partial = tmp_path / "partial"
    partial.mkdir()
    (partial / "save_data.json").write_text(
        (save_dir / "save_data.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    bundle = SaveBundle.load(partial)
    assert bundle.has("save_data.json")
    assert not bundle.has("global.json")
    assert bundle.global_data is None


def test_save_with_no_edits_is_a_noop(save_dir):
    originals = {
        name: (save_dir / name).read_text(encoding="utf-8")
        for name in ("global.json", "save_data.json", "settings.json")
    }
    original_mtimes = {name: (save_dir / name).stat().st_mtime_ns for name in originals}

    bundle = SaveBundle.load(save_dir)
    written = bundle.save()

    assert written == []
    assert not (save_dir / "hmd_editor_backups").exists()
    for name, text in originals.items():
        assert (save_dir / name).read_text(encoding="utf-8") == text
        assert (save_dir / name).stat().st_mtime_ns == original_mtimes[name]


def test_save_writes_only_changed_files_and_creates_one_backup(save_dir):
    bundle = SaveBundle.load(save_dir)
    bundle.set_value("save_data.json", ["cash"], 5000.0)

    written = bundle.save()

    assert written == ["save_data.json"]
    assert bundle.data("save_data.json")["cash"] == 5000.0

    backups = list((save_dir / "hmd_editor_backups").glob("save_data.json.*.json"))
    assert len(backups) == 1
    assert '"cash":150.0' in backups[0].read_text(encoding="utf-8")

    assert not list((save_dir / "hmd_editor_backups").glob("global.json.*.json"))
    assert not list((save_dir / "hmd_editor_backups").glob("settings.json.*.json"))

    # Saving again with no further edits is a no-op: no new backup.
    written_again = bundle.save()
    assert written_again == []
    assert len(list((save_dir / "hmd_editor_backups").glob("save_data.json.*.json"))) == 1


def test_set_value_coerces_numeric_type(save_dir):
    bundle = SaveBundle.load(save_dir)
    bundle.set_value("save_data.json", ["cash"], 5)  # int in, float field
    assert bundle.data("save_data.json")["cash"] == 5.0
    assert isinstance(bundle.data("save_data.json")["cash"], float)

    text = bundle.save()
    assert text == ["save_data.json"]
    assert '"cash":5.0' in (save_dir / "save_data.json").read_text(encoding="utf-8")


def test_set_value_nested_path(save_dir):
    bundle = SaveBundle.load(save_dir)
    bundle.set_value("save_data.json", ["dudes", "aaa", "hp_percent"], 0.5)
    assert bundle.data("save_data.json")["dudes"]["aaa"]["hp_percent"] == 0.5


def test_revert_discards_edits(save_dir):
    bundle = SaveBundle.load(save_dir)
    bundle.set_value("save_data.json", ["cash"], 1.0)
    assert bundle.is_dirty("save_data.json")

    bundle.revert("save_data.json")

    assert not bundle.is_dirty("save_data.json")
    assert bundle.data("save_data.json")["cash"] == 150.0


def test_backup_pruning_keeps_last_20(save_dir):
    bundle = SaveBundle.load(save_dir)
    for i in range(25):
        bundle.set_value("save_data.json", ["cash"], float(i))
        bundle.save()
        time.sleep(0.001)  # ensure distinct timestamps

    backups = list((save_dir / "hmd_editor_backups").glob("save_data.json.*.json"))
    assert len(backups) == 20

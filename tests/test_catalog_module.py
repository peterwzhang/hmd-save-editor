from hmd_editor.catalog import Catalog, get_catalog

SYNTHETIC = {
    "dentist": {
        "id": "dentist",
        "kind": "dude",
        "name": "Dentist Dude",
        "ability_name": "Novocaine Injection",
        "description": "Injects novocaine.",
        "sprite": "/sprites/sp_icon_dude_dentist_0.webp",
    },
    "r_bandage": {
        "id": "r_bandage",
        "kind": "relic",
        "name": "Bandage",
        "ability_name": None,
        "description": "Heals a bit.",
        "sprite": "/sprites/sp_relic_bandage_0.webp",
    },
}


def test_name_and_kind_lookup():
    cat = Catalog(SYNTHETIC)
    assert cat.name_for("dentist") == "Dentist Dude"
    assert cat.kind_for("dentist") == "dude"
    assert cat.ability_name_for("dentist") == "Novocaine Injection"
    assert cat.description_for("r_bandage") == "Heals a bit."


def test_unknown_id_falls_back_to_raw_id():
    cat = Catalog(SYNTHETIC)
    assert cat.name_for("r_totally_unknown") == "r_totally_unknown"
    assert cat.kind_for("r_totally_unknown") is None
    assert "r_totally_unknown" not in cat


def test_ids_of_kind():
    cat = Catalog(SYNTHETIC)
    assert cat.ids_of_kind("dude") == ["dentist"]
    assert cat.ids_of_kind("relic") == ["r_bandage"]
    assert cat.ids_of_kind("food") == []


def test_sprite_path_for_missing_local_file_returns_none():
    cat = Catalog(SYNTHETIC)
    # No cache/sprites/ dir alongside this synthetic catalog in general;
    # if the real repo's cache happens to have the file, that's fine too -
    # either way this must not raise.
    result = cat.sprite_path_for("dentist")
    assert result is None or result.is_file()


def test_real_catalog_loads_and_resolves_known_ids():
    cat = get_catalog()
    assert len(cat) > 0
    assert cat.name_for("dentist") == "Dentist Dude"
    assert cat.kind_for("r_bandage") == "relic"


def test_sprite_urls_returns_sorted_distinct_urls():
    cat = Catalog(SYNTHETIC)
    assert cat.sprite_urls() == [
        "/sprites/sp_icon_dude_dentist_0.webp",
        "/sprites/sp_relic_bandage_0.webp",
    ]


def test_clear_icon_cache_empties_memoized_lookups():
    # Deliberately doesn't call icon_for() here, which lazily imports
    # PySide6/QPixmap - this module stays testable without Qt or a display.
    cat = Catalog(SYNTHETIC)
    cat._icon_cache["dentist"] = "stand-in-for-a-qpixmap"

    cat.clear_icon_cache()

    assert cat._icon_cache == {}

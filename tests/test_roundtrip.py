from hmd_editor import jsonio


def test_roundtrip_is_byte_identical(fixtures_dir):
    for name in ("global.json", "save_data.json", "settings.json"):
        raw = (fixtures_dir / name).read_text(encoding="utf-8")
        obj = jsonio.loads(raw)
        out = jsonio.dumps(obj)
        assert out == raw, f"{name} did not round-trip byte-for-byte"


def test_seventeen_digit_float_preserved(fixtures_dir):
    raw = (fixtures_dir / "global.json").read_text(encoding="utf-8")
    assert "5682.3180138193011" in raw
    obj = jsonio.loads(raw)
    assert obj["minutes_played"].raw == "5682.3180138193011"
    # Python's shortest repr for this double drops a digit - the exact
    # scenario RawFloat exists to guard against.
    assert repr(float(obj["minutes_played"])) != "5682.3180138193011"
    out = jsonio.dumps(obj)
    assert "5682.3180138193011" in out


def test_edited_float_serializes_normally():
    obj = {"cash": jsonio.loads("150.0")}
    obj["cash"] = 999.0
    assert jsonio.dumps(obj) == '{"cash":999.0}'


def test_bool_and_none_and_nested_structures_roundtrip():
    raw = '{"a":true,"b":false,"c":null,"d":[1,2.5,"x"],"e":{"f":{}}}'
    assert jsonio.dumps(jsonio.loads(raw)) == raw

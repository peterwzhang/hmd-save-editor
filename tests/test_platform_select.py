from hmd_editor import platform_select


def test_is_wsl_true_when_microsoft_in_proc_version(tmp_path, monkeypatch):
    proc_version = tmp_path / "version"
    proc_version.write_text("Linux version 6.6.87.1-microsoft-standard-WSL2\n")
    monkeypatch.setattr(platform_select, "PROC_VERSION_PATH", proc_version)

    assert platform_select.is_wsl() is True


def test_is_wsl_false_on_regular_linux(tmp_path, monkeypatch):
    proc_version = tmp_path / "version"
    proc_version.write_text("Linux version 6.8.0-generic\n")
    monkeypatch.setattr(platform_select, "PROC_VERSION_PATH", proc_version)

    assert platform_select.is_wsl() is False


def test_is_wsl_false_when_proc_version_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(platform_select, "PROC_VERSION_PATH", tmp_path / "nope")

    assert platform_select.is_wsl() is False


def test_xcb_runtime_available_true_when_all_libs_load(monkeypatch):
    monkeypatch.setattr(platform_select.ctypes, "CDLL", lambda name: object())

    assert platform_select.xcb_runtime_available() is True


def test_xcb_runtime_available_false_when_any_lib_missing(monkeypatch):
    def fake_cdll(name):
        if name == platform_select.XCB_REQUIRED_LIBS[-1]:
            raise OSError("not found")
        return object()

    monkeypatch.setattr(platform_select.ctypes, "CDLL", fake_cdll)

    assert platform_select.xcb_runtime_available() is False


def test_preferred_qpa_platform_xcb_on_wsl_with_libs(monkeypatch):
    monkeypatch.setattr(platform_select, "is_wsl", lambda: True)
    monkeypatch.setattr(platform_select, "xcb_runtime_available", lambda: True)

    assert platform_select.preferred_qpa_platform() == "xcb"


def test_preferred_qpa_platform_none_when_not_wsl(monkeypatch):
    monkeypatch.setattr(platform_select, "is_wsl", lambda: False)
    monkeypatch.setattr(platform_select, "xcb_runtime_available", lambda: True)

    assert platform_select.preferred_qpa_platform() is None


def test_preferred_qpa_platform_none_when_libs_missing(monkeypatch):
    monkeypatch.setattr(platform_select, "is_wsl", lambda: True)
    monkeypatch.setattr(platform_select, "xcb_runtime_available", lambda: False)

    assert platform_select.preferred_qpa_platform() is None

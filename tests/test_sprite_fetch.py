import urllib.error
from unittest.mock import MagicMock, patch

from hmd_editor import sprite_fetch


def _mock_response(data: bytes):
    resp = MagicMock()
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    resp.read.return_value = data
    return resp


def test_missing_sprite_paths_skips_files_already_on_disk(tmp_path):
    (tmp_path / "a.webp").write_bytes(b"x")

    missing = sprite_fetch.missing_sprite_paths(
        ["/sprites/a.webp", "/sprites/b.webp"], tmp_path
    )

    assert missing == ["/sprites/b.webp"]


def test_download_sprites_writes_files_and_skips_existing(tmp_path):
    (tmp_path / "a.webp").write_bytes(b"already here")

    with patch(
        "hmd_editor.sprite_fetch.urllib.request.urlopen",
        return_value=_mock_response(b"fetched"),
    ) as urlopen, patch("hmd_editor.sprite_fetch.time.sleep"):
        failed = sprite_fetch.download_sprites(
            ["/sprites/a.webp", "/sprites/b.webp"], tmp_path
        )

    assert failed == []
    assert (tmp_path / "a.webp").read_bytes() == b"already here"  # untouched
    assert (tmp_path / "b.webp").read_bytes() == b"fetched"
    urlopen.assert_called_once()  # only the missing one was fetched


def test_download_sprites_reports_failures_without_aborting(tmp_path):
    def fake_urlopen(req, timeout):
        if "bad" in req.full_url:
            raise urllib.error.URLError("boom")
        return _mock_response(b"ok")

    with patch(
        "hmd_editor.sprite_fetch.urllib.request.urlopen", side_effect=fake_urlopen
    ), patch("hmd_editor.sprite_fetch.time.sleep"):
        failed = sprite_fetch.download_sprites(
            ["/sprites/bad.webp", "/sprites/good.webp"], tmp_path
        )

    assert failed == ["/sprites/bad.webp"]
    assert (tmp_path / "good.webp").read_bytes() == b"ok"
    assert not (tmp_path / "bad.webp").exists()


def test_download_sprites_reports_progress(tmp_path):
    calls = []

    with patch(
        "hmd_editor.sprite_fetch.urllib.request.urlopen",
        return_value=_mock_response(b"x"),
    ), patch("hmd_editor.sprite_fetch.time.sleep"):
        sprite_fetch.download_sprites(
            ["/sprites/a.webp", "/sprites/b.webp"],
            tmp_path,
            on_progress=lambda done, total: calls.append((done, total)),
        )

    assert calls == [(1, 2), (2, 2)]


def test_download_sprites_honors_cancellation(tmp_path):
    with patch(
        "hmd_editor.sprite_fetch.urllib.request.urlopen",
        return_value=_mock_response(b"x"),
    ) as urlopen, patch("hmd_editor.sprite_fetch.time.sleep"):
        sprite_fetch.download_sprites(
            ["/sprites/a.webp", "/sprites/b.webp"],
            tmp_path,
            should_cancel=lambda: True,
        )

    urlopen.assert_not_called()

from pathlib import Path

import pytest

from api.services.stt import moonshine_assets


def test_asset_manifest_is_pinned_to_reviewed_mit_english_release():
    assert moonshine_assets.MOONSHINE_PACKAGE_VERSION == "0.1.3"
    assert len(moonshine_assets.MOONSHINE_LINUX_WHEEL_SHA256) == 64
    assert moonshine_assets.MOONSHINE_SOURCE_TAG == "v0.1.3"
    assert moonshine_assets.MOONSHINE_MODEL_REVISION == "quantized_26_07_30"
    assert len(moonshine_assets.TINY_STREAMING_ASSETS) == 7
    assert sum(asset[1] for asset in moonshine_assets.TINY_STREAMING_ASSETS) == 51441771


def test_asset_verification_fails_closed_for_absent_or_changed_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(
        moonshine_assets,
        "TINY_STREAMING_ASSETS",
        (("model.ort", 3, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"),),
    )
    with pytest.raises(FileNotFoundError):
        moonshine_assets.verify_tiny_streaming_assets(tmp_path)

    (tmp_path / "model.ort").write_bytes(b"bad")
    with pytest.raises(ValueError, match="checksum"):
        moonshine_assets.verify_tiny_streaming_assets(tmp_path)

    (tmp_path / "model.ort").write_bytes(b"abc")
    assert moonshine_assets.verify_tiny_streaming_assets(tmp_path) == 3


def test_model_directory_must_be_the_reviewed_cache_without_path_traversal(tmp_path):
    expected = (
        tmp_path
        / "models"
        / "moonshine"
        / "tiny-streaming-en"
        / moonshine_assets.MOONSHINE_MODEL_REVISION
    )
    assert moonshine_assets.resolve_tiny_streaming_model_dir(
        "models/moonshine/tiny-streaming-en/quantized_26_07_30",
        service_root=tmp_path,
    ) == expected.resolve()

    with pytest.raises(ValueError, match="reviewed"):
        moonshine_assets.resolve_tiny_streaming_model_dir(
            "models/moonshine/../../outside", service_root=tmp_path
        )


def test_model_directory_rejects_a_symlinked_cache_root(tmp_path):
    models = tmp_path / "models"
    models.mkdir()
    external_cache = tmp_path / "external-cache"
    external_cache.mkdir()
    try:
        (models / "moonshine").symlink_to(external_cache, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are unavailable in this test environment")

    with pytest.raises(ValueError, match="symlinks"):
        moonshine_assets.resolve_tiny_streaming_model_dir(
            "models/moonshine/tiny-streaming-en/quantized_26_07_30",
            service_root=tmp_path,
        )


def test_asset_verification_rejects_symlinked_model_files(monkeypatch, tmp_path):
    monkeypatch.setattr(
        moonshine_assets,
        "TINY_STREAMING_ASSETS",
        (("model.ort", 3, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"),),
    )
    source = tmp_path / "source.ort"
    source.write_bytes(b"abc")
    link = tmp_path / "model.ort"
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip("symlinks are unavailable in this test environment")

    with pytest.raises(FileNotFoundError, match="absent"):
        moonshine_assets.verify_tiny_streaming_assets(tmp_path)

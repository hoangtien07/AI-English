import hashlib
import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "preseed_moonshine_tiny_streaming.py"
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location("moonshine_preseed_test", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Response:
    def __init__(self, body: bytes):
        self.body = body
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size: int) -> bytes:
        result = self.body[self.offset : self.offset + size]
        self.offset += len(result)
        return result


def test_download_keeps_existing_cache_file_when_staged_data_is_corrupt(monkeypatch, tmp_path):
    module = _load_script_module()
    destination = tmp_path / "model.ort"
    destination.write_bytes(b"known-good")
    monkeypatch.setattr(module, "urlopen", lambda *_args, **_kwargs: _Response(b"bad"))

    with pytest.raises(ValueError, match="checksum"):
        module._download(
            "https://invalid.test/model.ort",
            destination,
            3,
            hashlib.sha256(b"abc").hexdigest(),
        )

    assert destination.read_bytes() == b"known-good"
    assert not list(tmp_path.glob("tmp*"))


def test_preseed_rejects_output_outside_reviewed_model_cache(tmp_path):
    module = _load_script_module()
    with pytest.raises(ValueError, match="reviewed"):
        module.preseed(tmp_path / "outside", verify_only=True)

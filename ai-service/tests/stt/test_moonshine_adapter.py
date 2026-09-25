import sys
from types import SimpleNamespace

import numpy as np
import pytest

from api.services.stt.engines import moonshine
from api.services.stt.engines.moonshine import MoonshinePrimary, MoonshineSession


class FakeTranscript:
    def __init__(self, text):
        self.lines = [type("Line", (), {"text": text})()]


class FakeNativeTranscriber:
    MOONSHINE_FLAG_FORCE_UPDATE = 1

    def __init__(self):
        self.audio = []
        self.stopped = False

    def add_audio(self, samples, sample_rate):
        self.audio.extend(samples)

    def update_transcription(self, flags=0):
        return FakeTranscript("hello moonshine")

    def start(self):
        return None

    def stop(self):
        self.stopped = True

    def close(self):
        return None


@pytest.mark.asyncio
async def test_moonshine_adapter_converts_pcm_and_throttles_partial():
    native = FakeNativeTranscriber()
    session = MoonshineSession(native, "en")
    pcm = (np.ones(4800, dtype="<i2") * 1000).tobytes()
    result = await session.push_audio(pcm, 0, 300)
    assert result.text == "hello moonshine"
    assert max(native.audio) < 1.0
    await session.close()
    assert native.stopped


@pytest.mark.asyncio
async def test_primary_uses_verified_local_directory_not_auto_downloader(monkeypatch, tmp_path):
    verified_paths = []

    def verify(path):
        verified_paths.append(path)
        return 1

    class FakeTranscriber(FakeNativeTranscriber):
        def __init__(self, **kwargs):
            super().__init__()
            self.kwargs = kwargs

    fake_package = SimpleNamespace(
        ModelArch=SimpleNamespace(TINY_STREAMING="tiny-streaming"),
        Transcriber=FakeTranscriber,
    )
    monkeypatch.setattr(moonshine, "verify_tiny_streaming_assets", verify)
    monkeypatch.setitem(sys.modules, "moonshine_voice", fake_package)
    primary = MoonshinePrimary(model_dir=str(tmp_path))

    await primary.load()

    assert verified_paths == [tmp_path]
    assert primary._factory is not None

"""Run Moonshine tiny_streaming against an existing non-personal PCM WAV."""

from __future__ import annotations

import argparse
import asyncio
import time
import wave
from pathlib import Path
import sys

AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_ROOT))

from api.services.stt.engines.moonshine import MoonshinePrimary


def _read_pcm16_mono_16khz(path: Path) -> bytes:
    with wave.open(str(path), "rb") as wav:
        if (wav.getsampwidth(), wav.getnchannels(), wav.getframerate()) != (2, 1, 16000):
            raise ValueError("Smoke audio must be PCM16 mono at 16 kHz")
        return wav.readframes(wav.getnframes())


async def _run(audio: bytes, model_dir: str) -> tuple[str, float, float]:
    primary = MoonshinePrimary("tiny_streaming", model_dir)
    started = time.perf_counter()
    await primary.load()
    load_ms = (time.perf_counter() - started) * 1000
    session = await primary.create_session("en")
    try:
        started = time.perf_counter()
        await session.push_audio(audio, 0, len(audio) * 1000 // (16000 * 2))
        result = await session.finalize(None)  # The native stream owns this audio.
        transcribe_ms = (time.perf_counter() - started) * 1000
    finally:
        await session.close()
        await primary.close()
    return result.text, load_ms, transcribe_ms


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument(
        "--model-dir", default="models/moonshine/tiny-streaming-en/quantized_26_07_30"
    )
    args = parser.parse_args()
    text, load_ms, transcribe_ms = asyncio.run(_run(_read_pcm16_mono_16khz(args.audio), args.model_dir))
    if not text.strip():
        raise SystemExit("Moonshine smoke failed: empty transcript")
    print(f"Moonshine smoke passed: load_ms={load_ms:.1f} transcribe_ms={transcribe_ms:.1f} text={text!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

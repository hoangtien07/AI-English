# Deterministic local STT

LexiLingo's local primary is Moonshine Voice `0.1.3` with the English
`tiny_streaming` model only. It is an on-device, no-account/no-API-key path.
The manifest records the upstream MIT license claim for these English model
assets only; assess Moonshine Voice and every transitive dependency separately
before redistribution. Provenance is Moonshine git
tag `v0.1.3` at `db88bffd14574212b6094a2e230d4f328029c31b`, whose catalog pins
the model CDN revision `tiny-streaming-en/quantized_26_07_30`.

For the local Linux x86_64 container, the exact PyPI wheel is
`moonshine_voice-0.1.3-py3-none-manylinux_2_34_x86_64.whl`, SHA-256
`c48f852c353688da551c2ba73c7e6103bb8ca6d212b1723f07c053ee50722f55`.
Both AI Dockerfiles download that exact wheel, verify this checksum, and only
then install it; unsupported platforms fail the build rather than selecting a
different wheel silently.

The seven ignored assets occupy 51,441,771 bytes (about 49.1 MiB). Their exact
filenames, byte lengths and SHA-256 values are committed in
`api/services/stt/moonshine_assets.py`; the preseed script downloads only those
dated CDN URLs and verifies every file before returning. Downloads are
validated in a staging file before atomic replacement, and runtime validates
the same manifest without Moonshine's auto-downloader, so an absent or altered
cache simply leaves STT unavailable.

With the local Compose stack running (STT remains disabled until the last
step), provision and validate the cache from the Linux service image:

```powershell
docker compose -f docker-compose.dev.yml exec ai-service python scripts/preseed_moonshine_tiny_streaming.py
docker compose -f docker-compose.dev.yml exec ai-service python scripts/preseed_moonshine_tiny_streaming.py --verify-only
```

Before setting `STT_ENABLED=true` in the ignored root `.env`, run a smoke test
with a non-personal WAV at PCM16 mono 16 kHz (for example, a permitted fixture
from Moonshine's tagged repository). The command must report non-empty text and
its measured model-load/transcription latency. Do not enable STT if it fails:

```powershell
docker compose -f docker-compose.dev.yml exec ai-service python scripts/smoke_moonshine_tiny_streaming.py --audio path/to/non-personal-16k-mono.wav
```

The smoke output is local-only; it contains no secrets and should not use a
recording of a person without their permission. Once it passes, configure the
root `.env` with `STT_ENABLED=true`, retain `STT_DEGRADED_WHISPER_PRIMARY=false`,
and run `docker compose -f docker-compose.dev.yml up -d --build ai-service`.

An earlier local Linux-container smoke with Moonshine's non-personal tagged
`test-assets/beckett.wav` was reported as successful, but its output is not a
committed artifact. Treat it as historical context only and re-run the command
above before enabling STT; that command is the acceptance evidence. The host
Windows wheel previously raised a native DLL initialization error, so Windows
host execution remains unsupported until a compatible upstream wheel is
separately qualified.

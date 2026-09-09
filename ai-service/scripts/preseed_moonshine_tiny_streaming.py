"""Download the reviewed Moonshine model into the local ignored cache.

This is intentionally the only networked model-fetch path. The runtime checks
the same pinned hashes and never delegates to Moonshine's auto-downloader.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

# Scripts run with ``scripts/`` on sys.path; add the service root explicitly so
# this works from a fresh checkout without requiring an editable install.
AI_SERVICE_ROOT = Path(__file__).resolve().parents[1]
_ASSETS_PATH = AI_SERVICE_ROOT / "api/services/stt/moonshine_assets.py"
_SPEC = importlib.util.spec_from_file_location("lexilingo_moonshine_assets", _ASSETS_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - checkout corruption
    raise RuntimeError(f"Unable to load pinned Moonshine manifest: {_ASSETS_PATH}")
_ASSETS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_ASSETS)
MOONSHINE_MODEL_BASE_URL = _ASSETS.MOONSHINE_MODEL_BASE_URL
MOONSHINE_MODEL_REVISION = _ASSETS.MOONSHINE_MODEL_REVISION
TINY_STREAMING_ASSETS = _ASSETS.TINY_STREAMING_ASSETS
verify_tiny_streaming_assets = _ASSETS.verify_tiny_streaming_assets
verify_tiny_streaming_asset = _ASSETS.verify_tiny_streaming_asset
resolve_tiny_streaming_model_dir = _ASSETS.resolve_tiny_streaming_model_dir


DEFAULT_MODEL_DIR = Path("models/moonshine/tiny-streaming-en") / MOONSHINE_MODEL_REVISION


def _download(
    url: str, destination: Path, expected_size: int, expected_sha256: str
) -> None:
    request = Request(url, headers={"User-Agent": "LexiLingo-Moonshine-Preseed/1"})
    temporary_path: Path | None = None
    try:
        with urlopen(request, timeout=60) as response, tempfile.NamedTemporaryFile(
            mode="wb", dir=destination.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            while chunk := response.read(1024 * 1024):
                temporary.write(chunk)
            temporary.flush()
        # A transfer must validate while staged before it replaces a good
        # cache entry; an interrupted or corrupt file never reaches runtime.
        verify_tiny_streaming_asset(temporary_path, expected_size, expected_sha256)
        # The named handle must be closed before an atomic replacement on Windows.
        temporary_path.replace(destination)
    except BaseException:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def preseed(model_dir: Path, verify_only: bool = False) -> int:
    model_dir = resolve_tiny_streaming_model_dir(
        model_dir, service_root=AI_SERVICE_ROOT
    )
    if verify_only:
        return verify_tiny_streaming_assets(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    for filename, expected_size, expected_sha256 in TINY_STREAMING_ASSETS:
        destination = model_dir / filename
        try:
            verify_tiny_streaming_assets(model_dir)
            break
        except (FileNotFoundError, ValueError):
            pass
        _download(
            f"{MOONSHINE_MODEL_BASE_URL}/{filename}",
            destination,
            expected_size,
            expected_sha256,
        )
    return verify_tiny_streaming_assets(model_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    total_bytes = preseed(args.model_dir, args.verify_only)
    print(f"Moonshine tiny_streaming cache verified: {args.model_dir} ({total_bytes} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

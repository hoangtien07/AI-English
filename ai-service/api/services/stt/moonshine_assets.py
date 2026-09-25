"""Pinned provenance and local integrity checks for Moonshine tiny_streaming.

The entries are the English tiny-streaming dependency set from Moonshine Voice
v0.1.3 (git tag v0.1.3, commit db88bffd14574212b6094a2e230d4f328029c31b).
They deliberately live in source, while the downloaded binary files stay ignored.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


MOONSHINE_PACKAGE_VERSION = "0.1.3"
# Linux x86_64 wheel used by the pinned local Docker image. The native package
# is platform-specific, so this is recorded as provenance rather than applied
# as pip's global --require-hashes policy for the whole AI dependency graph.
MOONSHINE_LINUX_WHEEL_SHA256 = (
    "c48f852c353688da551c2ba73c7e6103bb8ca6d212b1723f07c053ee50722f55"
)
MOONSHINE_SOURCE_TAG = "v0.1.3"
MOONSHINE_SOURCE_COMMIT = "db88bffd14574212b6094a2e230d4f328029c31b"
MOONSHINE_MODEL_REVISION = "quantized_26_07_30"
# This records the upstream license claim for these *model assets* only.  It
# does not license Moonshine Voice itself or any of its transitive packages.
MOONSHINE_MODEL_LICENSE = "MIT (Moonshine English-language model assets; upstream claim)"
MOONSHINE_MODEL_BASE_URL = (
    "https://download.moonshine.ai/model/tiny-streaming-en/quantized_26_07_30"
)

# filename, bytes, SHA-256. Hashes were recorded from the immutable dated CDN
# revision above; no mutable `latest` URL is used by the preseed process.
TINY_STREAMING_ASSETS: tuple[tuple[str, int, str], ...] = (
    ("adapter.ort", 1319664, "22ecc949e146c49667fda28d102d4e30749a107dc88a396292aa8f277ef1347c"),
    ("cross_kv.ort", 1287544, "143a36667b8d05fd9d04e8c337b7ee121f37ef299aea6b3d82bdb3d3401950b4"),
    ("decoder_kv.ort", 32583720, "8852553f312adb6c9aa4d17418015049b30f412209ee569d336548c0044627de"),
    ("encoder.ort", 7675440, "a8414e1a5dedf9f2093d7680601dd8a9b0433e7020260eafe0e370ead91134ca"),
    ("frontend.ort", 8324920, "271a563251f11e6311949530f8025ed4d345c5d69d4ac1efa74093779927d636"),
    ("streaming_config.json", 509, "74fe5ddebd63b17caf59e8a3b18c17547ff7bce1642050edbb1c3962674f8950"),
    ("tokenizer.bin", 249974, "6884b35fd6377d4c4d32336a0bc152f36b64d1e45b6503683cdc238250a8472d"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_tiny_streaming_asset(
    path: str | Path, expected_size: int, expected_sha256: str
) -> None:
    """Verify one asset without following a cache-file symlink."""
    asset = Path(path)
    if asset.is_symlink() or not asset.is_file():
        raise FileNotFoundError(f"Moonshine tiny_streaming asset is absent: {asset}")
    actual_size = asset.stat().st_size
    if actual_size != expected_size:
        raise ValueError(
            f"Moonshine asset size mismatch for {asset}: "
            f"expected {expected_size}, got {actual_size}"
        )
    actual_sha256 = _sha256(asset)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"Moonshine asset checksum mismatch for {asset}: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )


def resolve_tiny_streaming_model_dir(
    model_dir: str | Path, *, service_root: str | Path
) -> Path:
    """Return the one reviewed cache location, rejecting traversal and aliases."""
    root = Path(service_root).resolve()
    cache_root = root / "models" / "moonshine"
    expected = cache_root / "tiny-streaming-en" / MOONSHINE_MODEL_REVISION
    # A symlinked cache root could redirect the native model loader outside of
    # the reviewed volume even when its visible path looks correct.
    if any(
        path.is_symlink()
        for path in (
            root / "models",
            cache_root,
            cache_root / "tiny-streaming-en",
            expected,
        )
    ):
        raise ValueError("Moonshine model cache path must not contain symlinks")
    configured = Path(model_dir)
    candidate = (configured if configured.is_absolute() else root / configured).resolve()
    if candidate != expected:
        raise ValueError(
            "STT_MOONSHINE_MODEL_DIR must be the reviewed "
            "models/moonshine/tiny-streaming-en/quantized_26_07_30 cache"
        )
    return candidate


def verify_tiny_streaming_assets(model_dir: str | Path) -> int:
    """Fail closed unless every pinned file is present and unmodified."""
    root = Path(model_dir)
    total_bytes = 0
    for filename, expected_size, expected_sha256 in TINY_STREAMING_ASSETS:
        asset = root / filename
        try:
            verify_tiny_streaming_asset(asset, expected_size, expected_sha256)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Moonshine tiny_streaming asset is absent: {asset}. "
                "Run scripts/preseed_moonshine_tiny_streaming.py before enabling STT."
            ) from exc
        total_bytes += expected_size
    return total_bytes

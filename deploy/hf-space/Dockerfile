# Hugging Face Spaces (Docker SDK) image for ai-service.
#
# A Space repo only contains this Dockerfile — the application source is
# cloned from GitHub at build time. Mirrors ai-service/Dockerfile.prod; the
# differences are the source (git clone instead of build context) and the
# listen port (HF routes external traffic to 7860, not 8001).
# KEEP IN SYNC with ai-service/Dockerfile.prod when dependencies or the
# model-download steps change.
#
# Build args let the Space track another branch without editing this file:
#   GIT_REF  (default: tienph)
#   REPO_URL (default: the public repo)

ARG REPO_URL=https://github.com/hoangtien07/AI-English.git
ARG GIT_REF=tienph

# ── fetch the pinned source ──────────────────────────────────────────────
FROM alpine:3.20 AS source
ARG REPO_URL
ARG GIT_REF
RUN apk add --no-cache git && \
    git clone --depth 1 --branch "${GIT_REF}" "${REPO_URL}" /repo

# ── builder: venv + pinned wheels + voice models ─────────────────────────
FROM python:3.11.13-slim-bookworm@sha256:86adf8dbadc3d6e82ee5dd2c74bec2e1c2467cdad47886280501df722372d2e1 AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv "${VIRTUAL_ENV}"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

WORKDIR /build
COPY --from=source /repo/ai-service/requirements.txt /repo/ai-service/constraints-ai.txt ./
RUN pip install --upgrade pip && \
    mkdir -p /build/moonshine-wheel && \
    pip download --no-deps --only-binary=:all: --dest /build/moonshine-wheel \
      moonshine-voice==0.1.3 && \
    echo "c48f852c353688da551c2ba73c7e6103bb8ca6d212b1723f07c053ee50722f55  /build/moonshine-wheel/moonshine_voice-0.1.3-py3-none-manylinux_2_34_x86_64.whl" | sha256sum -c - && \
    pip install --no-cache-dir --no-deps /build/moonshine-wheel/moonshine_voice-0.1.3-py3-none-manylinux_2_34_x86_64.whl && \
    rm -rf /build/moonshine-wheel && \
    pip install --no-cache-dir -c constraints-ai.txt -r requirements.txt \
      --extra-index-url https://download.pytorch.org/whl/cpu

RUN mkdir -p /opt/voice-models/piper && \
    curl --fail --location --retry 3 \
      https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx \
      --output /opt/voice-models/piper/en_US-lessac-medium.onnx && \
    curl --fail --location --retry 3 \
      https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json \
      --output /opt/voice-models/piper/en_US-lessac-medium.onnx.json && \
    echo "5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f  /opt/voice-models/piper/en_US-lessac-medium.onnx" | sha256sum -c - && \
    echo "efe19c417bed055f2d69908248c6ba650fa135bc868b0e6abb3da181dab690a0  /opt/voice-models/piper/en_US-lessac-medium.onnx.json" | sha256sum -c -

# Faster-Whisper verifier weights must be a LOCAL directory — the verifier
# refuses model IDs like "base.en" (see FasterWhisperVerifier.load). Bundle
# them at build time, pinned to a revision.
RUN python -c "\
from huggingface_hub import snapshot_download; \
snapshot_download(repo_id='Systran/faster-whisper-base.en', \
    revision='3d3d5dee26484f91867d81cb899cfcf72b96be6c', \
    local_dir='/opt/stt-models/faster-whisper-base.en')" && \
    rm -rf /opt/stt-models/faster-whisper-base.en/.cache

# ── runtime ──────────────────────────────────────────────────────────────
FROM python:3.11.13-slim-bookworm@sha256:86adf8dbadc3d6e82ee5dd2c74bec2e1c2467cdad47886280501df722372d2e1

# STT verifier + TTS voice resolve to the bundled models by default
ENV ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STT_VERIFY_MODEL=/opt/stt-models/faster-whisper-base.en \
    TTS_MODEL_PATH=en_US-lessac-medium \
    TTS_CONFIG_PATH=/opt/voice-models/piper/en_US-lessac-medium.onnx.json

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/voice-models /opt/voice-models
COPY --from=builder /opt/stt-models /opt/stt-models
COPY --from=source /repo/ai-service/api ./api
COPY --from=source /repo/ai-service/data ./data
COPY --from=source /repo/ai-service/service ./service

# Same import check as Dockerfile.prod — fail the build, not the runtime.
RUN SECRET_KEY=build-time-import-check-not-a-runtime-secret \
    python -c "import defusedxml, typer; from api.services.content_etl.cli import app; import api.main"

RUN mkdir -p /app/models /app/logs /tmp/lexilingo-stt && \
    chown -R appuser:appuser /app /tmp/lexilingo-stt

USER appuser

# HF Spaces route all external HTTP to port 7860.
EXPOSE 7860
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=5 \
  CMD python -c "import urllib.request; response = urllib.request.urlopen('http://127.0.0.1:7860/live', timeout=3); raise SystemExit(0 if response.status == 200 else 1)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1", "--proxy-headers"]

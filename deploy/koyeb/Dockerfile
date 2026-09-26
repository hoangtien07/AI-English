# Koyeb image for backend-service.
#
# Koyeb's git Dockerfile builder always uses the REPOSITORY ROOT as the build
# context (there is no docker-context option), so this Dockerfile mirrors
# backend-service/Dockerfile.prod with COPY sources prefixed by
# backend-service/. KEEP IN SYNC with backend-service/Dockerfile.prod.
#
# Koyeb service settings to pair with this file:
#   builder: docker | dockerfile path: deploy/koyeb/Dockerfile | port 8000
#   health check path: /health | instance type: free/nano

FROM python:3.13-slim as builder

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv "${VIRTUAL_ENV}"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

COPY backend-service/requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim

ENV APP_ENV=production \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY --from=builder /opt/venv /opt/venv
COPY backend-service/ .

RUN chmod +x scripts/entrypoint.sh && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["scripts/entrypoint.sh"]

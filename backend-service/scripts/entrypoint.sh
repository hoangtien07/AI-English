#!/usr/bin/env bash
# Production entrypoint — applies Alembic migrations before serving traffic.
#
# Logic:
#   Empty/versioned DB → alembic upgrade head
#   Unversioned DB     → refuse automatic adoption
#   DB unreachable     → skip migration step, start API so Render can bind port
#
# Usage:
#   ./scripts/entrypoint.sh            (production)
#   DATABASE_URL=postgresql+asyncpg://... ./scripts/entrypoint.sh

set -euo pipefail

echo "=== LexiLingo Backend Startup ==="
if [ -n "${DATABASE_URL:-}" ]; then
    echo "DATABASE_URL: <configured>"
else
    echo "DATABASE_URL: <not set>"
fi

# Check whether Alembic owns this schema. A populated schema without Alembic
# history is deliberately not adopted automatically: stamping it at head could
# conceal an incomplete legacy schema and make later upgrades unsafe.
DB_STATE=$(python - <<'EOF'
import asyncio
import sys
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

url = settings.async_database_url
if not url or url.startswith("sqlite"):
    print("skip")
    sys.exit(0)

async def check() -> str:
    engine = create_async_engine(url, pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as conn:
            version_table = await conn.scalar(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'alembic_version'"
            ))
            app_tables = await conn.scalar(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name != 'alembic_version'"
            ))
            if not app_tables:
                return "fresh"
            if not version_table:
                return "unversioned"
            version = await conn.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
            return "existing" if version is not None else "unversioned"
    except Exception as e:
        print(f"DB check failed ({type(e).__name__})", file=sys.stderr)
        return "unreachable"
    finally:
        await engine.dispose()

print(str(asyncio.run(check())))
EOF
)

case "$DB_STATE" in
    fresh)
        echo ">>> Fresh database detected — applying Alembic migrations..."
        alembic upgrade head
        echo ">>> Schema initialised from migrations."
        ;;
    existing)
        echo ">>> Existing database — applying pending Alembic migrations..."
        alembic upgrade head
        echo ">>> Migrations applied."
        ;;
    unversioned)
        echo ">>> ERROR: Database has tables but no Alembic history; refusing to stamp it automatically."
        echo ">>> Back up and reconcile the legacy schema before adopting it."
        exit 1
        ;;
    unreachable)
        echo ">>> WARNING: Database unreachable during startup probe. Skipping migrations and continuing to bind API port."
        echo ">>> WARNING: Check DATABASE_URL / network access on Render. Readiness checks may fail until DB is reachable."
        ;;
    skip)
        echo ">>> No production PostgreSQL database configured — skipping migration bootstrap."
        ;;
    *)
        echo ">>> ERROR: Unexpected database probe result: $DB_STATE"
        exit 1
        ;;
esac

echo ">>> Starting Uvicorn..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${UVICORN_WORKERS:-1}" \
    --proxy-headers \
    --forwarded-allow-ips="*"

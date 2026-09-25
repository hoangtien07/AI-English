# Local database bootstrap and minimal seed

The local bootstrap command is intentionally non-destructive. It never runs a
schema reset, drops a table, or removes a Docker volume.

From `backend-service`, first point `DATABASE_URL` at the intended local
database and inspect it:

```powershell
python -m scripts.bootstrap_local --check
```

For an empty database, run the command without `--check`. It runs
`alembic upgrade head`, which creates the schema from the repository's
migration history and records the resulting revision. A database that already
has `alembic_version` takes the same upgrade path. A populated database without
Alembic history is refused without modification; take a backup and reconcile it
explicitly instead of stamping an unknown schema.

```powershell
python -m scripts.bootstrap_local
python -m scripts.bootstrap_local
```

The second invocation is the existing-database path and should only apply any
new migrations. This is the supported restart/bootstrap sequence; do not use
`docker compose down -v` for ordinary local development.

## Local Gmail SMTP and admin access

For real local verification, resend, and password-reset emails, configure the
ignored `backend-service/.env` with `SMTP_HOST=smtp.gmail.com`,
`SMTP_PORT=587`, `SMTP_USE_TLS=true`, `SMTP_USE_SSL=false`, a bounded
`SMTP_TIMEOUT` (1--30 seconds), and matching `SMTP_USERNAME`/`EMAIL_FROM`.
Google requires 2-Step Verification and an App Password for SMTP; enter that
App Password only in the ignored `.env`, never in source control or logs.

Grant local admin access through comma-separated exact addresses in
`ADMIN_EMAIL_WHITELIST` and `SUPER_ADMIN_EMAIL_WHITELIST`. Addresses are
case-insensitive, and domain-wide entries or wildcards are rejected; the
super-admin address must sign in through the configured Google admin OAuth
client with a verified Google email.

The container entrypoint uses the same safety boundary: it upgrades an
Alembic-managed schema, initialises an empty one, and refuses a populated
unversioned database instead of silently stamping it.

## Minimal local seed

The minimal optional catalog seed is the built-in shop catalog:

```powershell
python -m scripts.seed_shop_items
python -m scripts.seed_shop_items
```

It performs an upsert by item name: the first run creates missing items and the
second updates those same rows without adding duplicates. `seed_demo_data.py`,
AI-generated content, and import/crawl scripts are intentionally outside the
minimal set because they create synthetic analytics users, need prerequisite
content, or may have separate source/provenance requirements.

## Isolated verification

Set `TEST_DATABASE_URL` to a database whose name ends in `_test` before
running backend tests. The test fixture refuses any other database name before
it recreates its test schema. The local-core regression suite exercises fresh
and versioned bootstrap states, runs the shop seed twice, exercises local
register/verify/login/me/refresh/logout without SMTP, and reopens an isolated
database connection to verify representative user/progress data persists.

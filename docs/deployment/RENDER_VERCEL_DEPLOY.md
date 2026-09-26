# Deploy — Render + Vercel

Topology:

```
admin.<domain>  (Vercel, admin-service SPA)
www.<domain>    (Vercel, flutter-app web build)
api.<domain>    (Render web service: lexilingo-backend)
ai.<domain>     (Render web service: lexilingo-ai)
                 ├── Render Postgres (private)
                 ├── Render Key Value / Redis (private)
                 └── MongoDB Atlas M0 (external — Render has no managed Mongo)
```

`render.yaml` at the repo root is the Blueprint. Frontends deploy separately to
Vercel via `scripts/deploy-*.sh` or the CD workflow.

## 1. Prerequisites

| Thing | Where | Notes |
|---|---|---|
| Render account | render.com | free tier works for a demo; `standard` recommended for ai-service |
| Vercel account | vercel.com | two projects: admin + flutter web |
| MongoDB Atlas M0 | cloud.mongodb.com | free; create cluster, db user, allow `0.0.0.0/0` or Render outbound IPs |
| Domain DNS | hoangtien07.me registrar | 4 CNAME/A records (step 4) |
| Google OAuth clients | console.cloud.google.com | web client exists (`403021618812-…`); admin may need its own |
| Firebase project | english-5d522 | service-account JSON for `FIREBASE_CREDENTIALS_JSON` |
| LLM keys | console.groq.com / aistudio | GROQ_API_KEYS (up to 7, comma-separated) and/or GEMINI_API_KEY |
| Gmail App Password | Google account | for SMTP_* password-reset emails (optional) |

## 2. Render backend stack

Dashboard → **New → Blueprint** → repo `hoangtien07/AI-English`, branch `tienph`.
Render provisions: `lexilingo-backend`, `lexilingo-ai`, `lexilingo-redis`,
`lexilingo-postgres`, and the `lexilingo-shared` env group (auto-generated
`SECRET_KEY`, `AI_ADMIN_API_KEY`, `LEARNER_STATE_INTERNAL_TOKEN`,
`AI_AUDIT_INGEST_SECRET`).

Fill the `sync: false` prompts when asked — or paste them in the Dashboard
after creation:

Backend:
- `ALLOWED_ORIGINS` = `https://admin.<domain>,https://www.<domain>`
- `ALLOWED_HOSTS` = `api.<domain>,<backend>.onrender.com`
- `APP_PUBLIC_URL` = `https://www.<domain>`
- `AI_SERVICE_URL` = `https://<ai-service>.onrender.com/api/v1`
- `LEARNER_STATE_API_URL` = `https://<backend>.onrender.com/api/v1/internal`
- `GOOGLE_CLIENT_ID`, `GOOGLE_ADMIN_CLIENT_ID`, `ADMIN_EMAIL_WHITELIST`,
  `SUPER_ADMIN_EMAIL_WHITELIST`
- `FIREBASE_PROJECT_ID`, `FIREBASE_CREDENTIALS_JSON` (service-account JSON)
- `SMTP_*`, `EMAIL_FROM`, `PASSWORD_RESET_URL_BASE_PRODUCTION`,
  `EMAIL_VERIFICATION_URL_BASE_PRODUCTION` (optional)
- `YOUTUBE_API_KEY`/`NEWSAPI_KEY`/`NEWSDATA_KEY` (optional content APIs)

AI service:
- `ALLOWED_ORIGINS` = `https://admin.<domain>,https://www.<domain>` — required;
  the production validator rejects the built-in localhost defaults
- `MONGODB_ATLAS_URI` = `mongodb+srv://user:pass@cluster.mongodb.net/`
- `LEARNER_STATE_API_URL` = same backend internal URL as above
- `GROQ_API_KEYS` and/or `GEMINI_API_KEY` — without either, AI chat falls back
  to templates and looks "alive but dumb"
- `STT_MODEL_NAME=small` on `standard` — bump plan before raising to large-v3

Backend runs `alembic upgrade head` in `scripts/entrypoint.sh` on every boot —
first deploy migrates the empty Postgres automatically.

## 3. Vercel frontends

Admin (repo already has `admin-service/vercel.json`):

```bash
cd admin-service
vercel link            # or create project admin-lexilingo in dashboard
cp .env.production.example .env.production   # fill VITE_* values
ENABLE_HOSTED_DEPLOYMENTS=1 bash ../scripts/deploy-admin-vercel.sh
```

`deploy-admin-vercel.sh` validates the env, injects the API origins into the
CSP `connect-src`, builds, and `vercel deploy --prod --prebuilt`.

Flutter web:

```bash
cd flutter-app
# fill assets/env/prod_config (API_BASE_URL=https://api.<domain>, …)
bash ../scripts/deploy-flutter-vercel.sh
```

Or use the CD workflow (`.github/workflows/cd.yml`): set repo variable
`ENABLE_HOSTED_DEPLOYMENTS=true`, add `VERCEL_TOKEN`, `VERCEL_ORG_ID`,
`VERCEL_PROJECT_ID_ADMIN`, `VERCEL_PROJECT_ID_FLUTTER`, plus the
`FIREBASE_WEB_*` / `PUBLIC_*` variables it lists, then run it manually.

## 4. DNS

| Record | Type | Target |
|---|---|---|
| `api.<domain>` | CNAME | `<backend>.onrender.com` (Render → service → Settings → Custom Domain) |
| `ai.<domain>` | CNAME | `<ai>.onrender.com` |
| `admin.<domain>` | CNAME / A | `cname.vercel-dns.com` (Vercel → project → Domains) |
| `www.<domain>` / apex | CNAME / A | Vercel per its DNS instructions |

Render and Vercel both issue TLS automatically once DNS resolves.

## 5. Smoke check

```bash
curl https://api.<domain>/health            # {"status":"ok"...}
curl https://ai.<domain>/live               # {"status":"alive"...}
# admin login via Google OAuth on https://admin.<domain>
```

## Sizing notes

- Free Render web services sleep after ~15 min idle → ~50 s cold starts.
- `plan: free` Postgres expires after 30 days — export (`pg_dump`) or upgrade.
- ai-service `standard` (2 GB) fits `STT_MODEL_NAME=small`; `large-v3` wants ~4 GB.
- Celery worker/beat are excluded — workers aren't free-tier and reminders are
  off (`REMINDERS_ENABLED=false`). Add `type: worker` services to render.yaml
  when enabling them.

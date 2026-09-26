# Deploy — Free Stack (Koyeb + HF Spaces + Neon + Upstash + Atlas + Vercel)

$0/month topology — no credit card required on any of these platforms
(Oracle/AWS/etc. need one; this stack does not).

```
admin.<domain>  (Vercel, admin-service SPA)
www.<domain>    (Vercel, flutter-app web build)
<app>.koyeb.app (Koyeb free web service: backend-service)
<u>-<s>.hf.space (Hugging Face Space, Docker SDK: ai-service)
                 ├── Neon            (Postgres serverless, 0.5 GB free)
                 ├── Upstash         (Redis over TLS, free)
                 └── MongoDB Atlas   (M0, free)
```

| Piece | Host | Why |
|---|---|---|
| backend-service | Koyeb free web service | Dockerfile deploy, always-on nano instance, ~512 MB |
| ai-service | HF Spaces (Docker SDK) | the only free tier with enough RAM (16 GB) for torch + STT |
| Postgres | Neon | serverless, `sslmode=require`, scales to zero |
| Redis | Upstash | `rediss://` TLS URL works as-is (`redis.from_url`) |
| MongoDB | Atlas M0 | ai-service DB |
| Frontends | Vercel | unchanged from the Render plan |

**Caveats of $0:** Neon and HF sleep when idle (first request after idle is a
cold start — HF Space sleeps after ~48h inactivity; STT model re-downloads on
first use after a rebuild). Free tiers have no SLA; treat as demo/personal tier.

---

## 0. Generate shared secrets

Four values must be **identical on backend and ai-service**. Generate once:

```bash
openssl rand -hex 32   # run 4 times →
# SECRET_KEY                    (JWT — shared between services)
# AI_ADMIN_API_KEY              (backend → ai-service X-Admin-Key)
# LEARNER_STATE_INTERNAL_TOKEN  (ai-service → backend internal channel)
# AI_AUDIT_INGEST_SECRET        (ai-service → backend audit ingest)
```

## 1. Neon (Postgres)

1. neon.tech → New Project → region closest to Koyeb's.
2. Copy the **direct** connection string (host WITHOUT `-pooler`):
   `postgresql://user:pass@ep-xxx.neon.tech/lexilingo?sslmode=require`
   - asyncpg ≥0.31 understands `sslmode=require` — keep it.
   - Do not use the `-pooler` endpoint: it is PgBouncer transaction mode and
     asyncpg prepared statements break under it.

## 2. Upstash (Redis)

1. console.upstash.com → Create Database → type **Redis** (not Vector/Queue).
2. Copy the TLS endpoint: `rediss://default:pass@xxx.upstash.io:6379`
   - Both services accept `rediss://` natively.
   - Optional: free tier is ~10k commands/day — enough for a personal demo.

## 3. MongoDB Atlas M0

Same as the Render plan: create M0 cluster → database user → Network Access
`0.0.0.0/0` → copy `mongodb+srv://...` URI.

> `0.0.0.0/0` is required only because HF Spaces have no fixed egress IPs and
> Atlas M0 does not support private endpoints. Mitigate it: use a long random
> DB password (the URI is the only barrier left), enable Atlas alert on
> unusual access, and tighten the allowlist if ai-service moves somewhere
> with static egress later.

## 4. Koyeb — backend-service

Dashboard → **Create Service → GitHub** → repo `hoangtien07/AI-English`,
branch `tienph`:

| Setting | Value |
|---|---|
| Builder | Dockerfile |
| Dockerfile path | `deploy/koyeb/Dockerfile` |
| Port / route | `8000` |
| Health check | `/health` |
| Instance | free / nano |
| Region | nearest free region |

Environment variables (same list as `render.yaml` — paste in Koyeb's env UI):

```
DATABASE_URL=<Neon direct URL>
REDIS_URL=<Upstash rediss:// URL>
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
PORT=8000
ENABLE_APP_CORS=true
CORS_ALLOW_ORIGIN_REGEX=
ALLOWED_ORIGINS=https://admin.<domain>,https://www.<domain>
ALLOWED_HOSTS=<app>.koyeb.app,api.<domain>
APP_PUBLIC_URL=https://www.<domain>
AI_SERVICE_URL=https://<user>-<space>.hf.space/api/v1
SECRET_KEY=<shared>
AI_ADMIN_API_KEY=<shared>
LEARNER_STATE_ENABLED=true
LEARNER_STATE_INTERNAL_TOKEN=<shared, ≥32 chars>
LEARNER_STATE_API_URL=https://<app>.koyeb.app/api/v1/internal
AI_AUDIT_INGEST_SECRET=<shared>
GOOGLE_CLIENT_ID=403021618812-7jd4j9l70jeakjlt6jpv86dogmqut6lo.apps.googleusercontent.com
GOOGLE_ADMIN_CLIENT_ID=<same or a dedicated admin client>
ADMIN_EMAIL_WHITELIST=<your email>
SUPER_ADMIN_EMAIL_WHITELIST=<your email>
FIREBASE_PROJECT_ID=english-5d522
FIREBASE_CREDENTIALS_JSON=<service-account JSON, one line>
REMINDERS_ENABLED=false
# optional email — without SMTP_* the API answers but only logs the mail:
SMTP_HOST=  SMTP_PORT=587  SMTP_USE_TLS=true  SMTP_USERNAME=  SMTP_PASSWORD=
EMAIL_FROM=
PASSWORD_RESET_URL_BASE_PRODUCTION=https://www.<domain>/reset-password
EMAIL_VERIFICATION_URL_BASE_PRODUCTION=https://www.<domain>/verify-email
# optional content APIs:
YOUTUBE_API_KEY=  NEWSAPI_KEY=  NEWSDATA_KEY=
```

The entrypoint runs `alembic upgrade head` on boot — first deploy migrates the
empty Neon DB automatically. `/health` must return 200 for the deploy to pass.

## 5. Hugging Face Space — ai-service

1. huggingface.co → **New Space** → name e.g. `lexilingo-ai` → SDK **Docker**
   → hardware **CPU basic (free)** → visibility Private is fine.
2. In the Space's **Files** tab upload `deploy/hf-space/Dockerfile` from this
   repo, renamed to `Dockerfile` (or `git clone` the space repo, copy the file
   in, push). It fetches `tienph` at build time — for reproducible deploys set
   Space variable `GIT_REF` to a **full** commit SHA instead of the moving
   branch (a rebuild with a branch ref silently pulls newer code).
3. Space **Settings → Variables and secrets**:

```
ALLOWED_ORIGINS=https://admin.<domain>,https://www.<domain>
CORS_ALLOW_ORIGIN_REGEX=
MONGODB_ATLAS_URI=mongodb+srv://...
MONGODB_DATABASE=lexilingo
MONGODB_TLS_ALLOW_INVALID_CERTIFICATES=false
REDIS_URL=<same Upstash rediss:// URL>
SECRET_KEY=<shared>
AI_ADMIN_API_KEY=<shared>
LEARNER_STATE_INTERNAL_TOKEN=<shared>
LEARNER_STATE_API_URL=https://<app>.koyeb.app/api/v1/internal
AI_AUDIT_INGEST_SECRET=<shared>
GROQ_API_KEYS=<comma-separated, up to 7>
GEMINI_API_KEY=
HUGGINGFACE_API_KEY=
STT_DEVICE=cpu
STT_COMPUTE_TYPE=int8
VOICE_DUPLEX_ENABLED=false
```

No `STT_VERIFY_MODEL`/`TTS_*` needed — the image bundles faster-whisper
`base.en` weights (`/opt/stt-models/…`) and the Piper voice
(`/opt/voice-models/…`), and both default envs point at them.

4. After build, the service is at `https://<user>-<space>.hf.space` — check
   `/live` returns 200 (models may still be loading → `/health` later).

> HF Spaces do not support custom domains on free CPU — browsers call the
> `*.hf.space` origin directly (already covered by `ALLOWED_ORIGINS`). If you
> want `ai.<domain>` anyway, front it with a Cloudflare Worker that rewrites
> the Host header — optional, not covered here.

## 6. Vercel frontends

Two projects as in the Render guide. Environment:

| Var | Value |
|---|---|
| `VITE_BACKEND_URL` | `https://<app>.koyeb.app/api/v1` (or `https://api.<domain>/api/v1`) |
| `VITE_AI_URL` | `https://<user>-<space>.hf.space/api/v1` |
| `VITE_PUBLIC_WEB_URL` | `https://www.<domain>` |

The `/api/v1` suffix is required — `ENV.backendUrl`/`aiUrl` are used verbatim
(`${ENV.backendUrl}/admin/...`), the frontends append no prefix themselves.

`scripts/deploy-admin-vercel.sh` injects both API origins into the CSP
`connect-src` — run it per the Render guide, same commands.

## 7. DNS (optional)

- `api.<domain>` → Koyeb custom domain (CNAME to `<app>.koyeb.app`; enable the
  domain in the service's Domains settings — verify it is offered on your plan)
- `admin.`/`www.` → Vercel as before
- `ai.<domain>` → not available on free HF Spaces; keep the `hf.space` URL in
  `VITE_AI_URL`

## 8. Smoke check

```bash
curl https://<app>.koyeb.app/health          # backend up + migrated
curl https://<user>-<space>.hf.space/live    # ai-service up
```

Then open `https://admin.<domain>`, sign in with Google, and confirm the admin
dashboard loads (proves CORS + JWT + DB end-to-end).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Koyeb build fails on `COPY` | wrong Dockerfile path — must be `deploy/koyeb/Dockerfile` (context is repo root) |
| Backend crash-loops on boot | missing shared secret or `LEARNER_STATE_INTERNAL_TOKEN` < 32 chars; or Neon URL has `-pooler` in the host |
| ai-service never goes live | `ALLOWED_ORIGINS`/`CORS_ALLOW_ORIGIN_REGEX` unset — prod validator rejects localhost defaults |
| Referral/password emails only logged | SMTP_* left empty — expected on free tier unless you add Gmail App Password |
| First AI request takes minutes | HF Space cold start + STT model download — normal on free CPU |

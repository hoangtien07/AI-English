# Security Policy

## Reporting Security Issues

**DO NOT** report security vulnerabilities through public GitHub issues.

Instead, please report them via email to: [your-security-email@example.com]

Include as much information as possible:
- Type of issue (credential leak, vulnerability, etc.)
- Affected files or components
- Steps to reproduce
- Potential impact

## Current Security Alerts

### Repository history and credentials

AI-English uses an independent clean-snapshot history on `origin`; it does not
rewrite or publish the upstream repository's history. The historical upstream
remains a fetch-only local reference under the documented upstream-sync policy.
Current-tree secret scans and required test gates must pass before an approved
import is committed. Do not interpret this policy as evidence that any external
account, credential rotation, or provider integration has been activated.

If a credential is found, revoke or rotate it through the account owner and
remove it from tracked material. Never copy a credential into an issue, pull
request, commit message, or documentation.

### Action Items for Repository Owner

1. **MongoDB Atlas Credentials**:
   - Go to [MongoDB Atlas](https://cloud.mongodb.com/)
   - Navigate to Database Access → Your User
   - Click "Edit" → "Edit Password"
   - Generate new secure password
   - Update local `.env` files with new credentials

2. **Google API Keys (Firebase)**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to APIs & Services → Credentials
   - Find the exposed API keys and click "Delete"
   - Create new API keys with proper restrictions:
     - Application restrictions: HTTP referrers (websites)
     - API restrictions: Limit to required APIs only
   - Keep mobile service-account material and OAuth client secrets out of the
     repository. Firebase Web client identifiers are public browser
     configuration and are handled under the narrow policy below.

3. **Clean snapshot policy**:
   - Do not rewrite the independent `origin` history to remediate an upstream
     history concern.
   - Follow [the upstream sync policy](../docs/UPSTREAM_SYNC_POLICY.md) for a
     reviewed, provenance-recorded cherry-pick or patch instead.

## Best Practices

### Never Commit:
- ❌ API keys
- ❌ Database passwords
- ❌ OAuth tokens
- ❌ Private keys
- ❌ Firebase Admin SDK service-account files and OAuth client secrets
- ❌ `.env` files with real credentials

### Always Use:
- ✅ Environment variables (`.env.example` as template)
- ✅ GitHub Secrets for CI/CD
- ✅ Secret management services (AWS Secrets Manager, HashiCorp Vault)
- ✅ `.gitignore` for sensitive files
- ✅ Git hooks to prevent accidental commits

### Development Setup:
1. Copy `.env.example` to `.env`
2. Fill in your local credentials in `.env`
3. Never commit `.env` file
4. Use different credentials for dev/staging/production

### For Flutter/Firebase:
```dart
// Firebase Web config is public browser configuration, not a server secret.
// Only the owned Web fields in firebase_options.dart and firebase-messaging-sw.js
// may be committed; the security sentinel rejects the same values elsewhere.
```

Do not commit Firebase Admin SDK service-account JSON, OAuth client secrets, or
unrestricted provider keys. Restrict the Firebase Web API key by authorized
referrers and API permissions even though it is intentionally public.

## Security Checklist

- [ ] All exposed credentials have been rotated
- [ ] `.gitignore` updated to prevent future leaks
- [ ] GitHub Secret Scanning alerts reviewed and closed
- [ ] Team members notified about security best practices
- [ ] CI/CD updated to use GitHub Secrets
- [ ] Documentation updated with security guidelines

## Resources

- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [12-Factor App Config](https://12factor.net/config)

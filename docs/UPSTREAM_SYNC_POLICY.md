# Upstream Sync Policy

## Purpose and repository roles

AI-English is independently maintained at
`https://github.com/hoangtien07/AI-English`. Its approved `origin` model is an
independent orphan clean-snapshot history, rooted at baseline commit
`ba243ba3881321efcbea0e68f8466ad072ac0843` (`chore: independent local clean
snapshot`). This clean snapshot replaces any plan to rewrite history.

`https://github.com/InfinityZero3000/LexiLingo` is an attribution-preserving,
fetch-only upstream reference. The local `upstream` remote may be used as a
private bridge for inspection and approved imports; its push URL must remain
disabled. It is not an origin, deployment target, or destination for this
repository's refs.

The upstream MIT license, copyright, and permission notice remain preserved in
[`LICENSE`](../LICENSE). This policy does not grant rights to content, data,
accounts, credentials, brands, or external services.

## Allowed import model

For an upstream change that is genuinely needed:

1. Fetch or inspect the local/private upstream bridge only as needed; do not
   change its remote configuration or push any ref to it.
2. Identify an exact source commit SHA and affected paths. Evaluate the change
   for licensing, data rights, runtime coupling, and secret exposure.
3. Create a focused AI-English branch and import only a reviewed change by
   selective `git cherry-pick` or a manually reviewed patch. Never merge
   unrelated histories and never merge the upstream branch wholesale.
4. Record provenance in the importing commit or adjacent change record:
   upstream repository URL, source SHA, source paths, import method,
   reviewer/approval, license assessment, and any adaptation made.
5. Run the required gates before committing or merging: current-tree secret
   sentinel, `git diff --check`, affected tests, and the specialist reviews
   required by `AGENTS.md`. Security review is mandatory when the import
   affects auth, API, database schema, environment/configuration, credentials,
   or deployment inputs.
6. Confirm no upstream refs, remote configuration, credentials, or external
   activation were changed. Push only approved AI-English refs to `origin`.

## Import record template

```text
Upstream provenance:
- Source: https://github.com/InfinityZero3000/LexiLingo
- Source SHA: <full immutable commit SHA>
- Paths reviewed: <paths>
- Import method: cherry-pick | reviewed patch
- License/rights assessment: <result>
- Adaptations: <summary>
- Gates: secret sentinel; git diff --check; <affected tests/reviews>
- Reviewer/approval: <name or record>
```

Do not use a branch name, tag, screenshot, or mutable URL as a substitute for
the source SHA. Do not place secrets, access tokens, passwords, or provider
configuration values in an import record.

## Current boundaries and integration facts

- Firebase CLI authentication is available and the sole owned Web app **AI
  English Web** is registered with its public Web SDK configuration. Google
  provider/support-email and local authorized-domain setup still require
  Firebase Console confirmation.
- A Gmail password exists only in ignored `backend-service/.env`. Its presence
  must not be logged or committed. Gmail `EHLO`, STARTTLS, authentication, and
  NOOP passed without sending an email; end-to-end delivery remains separate.
- No import may reintroduce a dependency on original deployments, accounts,
  domains, user data, secrets, or provider configuration.

## Prohibited actions

- Do not merge unrelated histories or rewrite the independent `origin` history.
- Do not push, create, delete, or alter upstream refs; upstream push remains
  disabled.
- Do not copy upstream production data, credentials, account configuration, or
  private media.
- Do not claim an external service, Firebase app, SMTP sender, or deployment is
  active without the required recorded gate evidence and authorization.

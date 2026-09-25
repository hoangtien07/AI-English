# Backend isolated test database

With the root local Compose PostgreSQL service running, run this from
`backend-service`:

```powershell
python -m scripts.run_isolated_tests
```

The command reads the local Compose PostgreSQL credentials from the root
`.env` without displaying them. It creates a uniquely named database ending in
`_test`, runs the full `tests` suite with both `DATABASE_URL` and
`TEST_DATABASE_URL` pointed there, then terminates only that database's test
connections and removes that exact database. Its per-run pytest temporary
directory is removed too; pre-existing `.pytest-tmp` contents are untouched.
It never resets the Compose application database or removes a Compose volume.

Forward pytest options after `--`:

```powershell
python -m scripts.run_isolated_tests -- -x
```

If the PostgreSQL role lacks `CREATEDB`, the command stops before pytest. Give
the local Compose role that capability, or use the normal local Compose role;
do not point the command at an existing database.

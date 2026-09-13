# LexiLingo repository approval register v1

The machine-readable authority is [open-data-source-register-v1.json](open-data-source-register-v1.json). Its canonical repository path is the sole trust root for `backend-service/scripts/import_approved_course_artifact.py`; the importer intentionally has no `--source-register` option and does not accept caller-supplied approval data.

## Authoritative schema

The JSON root has exactly `schema` (`lexilingo.open-data-source-register`), `schema_version` (`2`), `title`, and `sources`. Each source has exactly `source_id`, `artifact_source_name`, `display_name`, `status`, `blocked_reason`, `source_version`, `snapshot_id`, `raw_checksum`, `license_id`, `official_url`, and `allowed_usage`.

`source_id` is one of exactly `source-oewn-2025`, `source-cmudict`, `source-cefr-j`, or `source-evc-beginning-ell`; duplicates and unknown IDs are rejected. `status` is explicitly either `approved` or `blocked`: only the first three IDs may be approved, and only Evergreen may be blocked. An approved record has a lowercase 64-hex `raw_checksum` and a null `blocked_reason`; the Evergreen record has a non-empty `blocked_reason` and a null checksum.

An artifact manifest is accepted only when its `source_name` equals an approved record's `artifact_source_name`, and its `source_version`, `snapshot_id`, `raw_checksum`, `license_id`, and `official_url` exactly equal that record. Every vocabulary `content_usage` for the source must be in its `allowed_usage`; unlisted or deferred sources, including Common Voice, cannot pass this boundary.

## Pins and status

| Source ID | Artifact source name | Status | Allowed usage |
|---|---|---|---|
| `source-oewn-2025` | `oewn` | approved | `lexical` |
| `source-cmudict` | `cmudict` | approved | `pronunciation` |
| `source-cefr-j` | `cefr_j` | approved | `lexical` |
| `source-evc-beginning-ell` | `oer_curriculum` | blocked | `curriculum_skeleton` |

Evergreen remains blocked because no approved immutable offline snapshot exists. This register does not approve Common Voice, LibriSpeech, Tatoeba, Wikidata, or repository-local unverified datasets.

## Import boundary

The importer accepts only a regular, non-symlink artifact under the repository root; it limits bytes and JSON depth/counts before model validation, and parses/hashes each file from one bounded byte buffer. `--apply --local-database` remains draft-only and delegates to `ContentAgentApplyService`, but requires the development application profile plus either the exact non-symlink `backend-service/.local-dev/lexilingo-importer.sqlite3` path or loopback PostgreSQL identity `lexilingo_dev` / `lexilingo_dev`; URI, query, and identity ambiguity fail closed.

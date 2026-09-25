"""Structural checks for the repository-local data provenance catalog."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPOSITORY_ROOT / "docs" / "LOCAL_DATA_PROVENANCE_MANIFEST.json"


class LocalDataProvenanceManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_required_top_level_structure(self) -> None:
        manifest = self.manifest
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["scope"].split(".")[0], "Repository-local inventory only")
        self.assertTrue(manifest["sources"])
        self.assertTrue(manifest["artifacts"])
        self.assertTrue(manifest["seed_entrypoints"])

    def test_ids_are_unique_per_collection(self) -> None:
        for collection_name in ("sources", "artifacts", "seed_entrypoints"):
            identifiers = [item["id"] for item in self.manifest[collection_name]]
            with self.subTest(collection=collection_name):
                self.assertEqual(len(identifiers), len(set(identifiers)))
                self.assertTrue(all(identifier.strip() for identifier in identifiers))

    def test_artifact_source_and_seed_foreign_keys_are_valid(self) -> None:
        source_ids = {source["id"] for source in self.manifest["sources"]}
        entrypoint_ids = {entrypoint["id"] for entrypoint in self.manifest["seed_entrypoints"]}
        allowed_statuses = set(self.manifest["policy"]["catalog_statuses"])
        allowed_dispositions = set(self.manifest["policy"]["usage_dispositions"])

        for artifact in self.manifest["artifacts"]:
            with self.subTest(artifact=artifact["id"]):
                self.assertTrue(artifact["paths"])
                self.assertTrue(artifact["source_refs"])
                self.assertIn(artifact["status"], allowed_statuses)
                self.assertIn(artifact["usage_disposition"], allowed_dispositions)
                self.assertTrue(set(artifact["source_refs"]).issubset(source_ids))
                self.assertTrue(
                    set(artifact.get("seed_entrypoint_refs", [])).issubset(entrypoint_ids)
                )

    def test_catalog_paths_resolve_inside_the_repository(self) -> None:
        catalog_paths = [
            path
            for artifact in self.manifest["artifacts"]
            for path in artifact["paths"]
        ] + [entrypoint["path"] for entrypoint in self.manifest["seed_entrypoints"]]
        for relative_path in catalog_paths:
            with self.subTest(path=relative_path):
                self.assertFalse(Path(relative_path).is_absolute())
                self.assertTrue(
                    list(REPOSITORY_ROOT.glob(relative_path)),
                    f"catalog path does not resolve: {relative_path}",
                )

    def test_entrypoint_artifact_foreign_keys_are_valid(self) -> None:
        artifact_ids = {artifact["id"] for artifact in self.manifest["artifacts"]}
        for entrypoint in self.manifest["seed_entrypoints"]:
            with self.subTest(entrypoint=entrypoint["id"]):
                self.assertTrue(entrypoint["path"])
                self.assertTrue(entrypoint["idempotency"])
                self.assertTrue(set(entrypoint["input_artifact_refs"]).issubset(artifact_ids))


if __name__ == "__main__":
    unittest.main()

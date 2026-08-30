from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

import pytest

from vaultcanary.adapters import load_export
from vaultcanary.audit import AuditError, audit_manifest, load_manifest
from vaultcanary.generate import build_bundle


def _write_bundle_files(tmp_path: Path, seed: str = "audit") -> tuple[Path, Path]:
    bundle = build_bundle(seed=seed)
    manifest_path = tmp_path / "manifest.json"
    export_path = tmp_path / "return.json"
    manifest_path.write_text(json.dumps(bundle.manifest), encoding="utf-8")
    export_path.write_text(json.dumps(bundle.probe), encoding="utf-8")
    return manifest_path, export_path


def test_untouched_probe_preserves_every_feature(tmp_path: Path) -> None:
    manifest_path, export_path = _write_bundle_files(tmp_path)
    manifest = load_manifest(manifest_path)
    vault = load_export(export_path, title_prefix=manifest.title_prefix)

    report = audit_manifest(manifest, vault)

    assert report.ok is True
    assert report.preserved_count == 17
    assert report.relocated_count == 0
    assert report.missing_count == 0
    assert {result.status for result in report.results} == {"preserved"}


def test_audit_distinguishes_relocated_and_missing_values(tmp_path: Path) -> None:
    bundle = build_bundle(seed="lossy")
    login = bundle.probe["items"][0]
    hidden = login["fields"].pop(1)["value"]
    login["notes"] = hidden
    login["login"].pop("password")
    manifest_path = tmp_path / "manifest.json"
    export_path = tmp_path / "return.json"
    manifest_path.write_text(json.dumps(bundle.manifest), encoding="utf-8")
    export_path.write_text(json.dumps(bundle.probe), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    report = audit_manifest(manifest, load_export(export_path, title_prefix=manifest.title_prefix))
    by_id = {result.feature_id: result for result in report.results}

    assert report.ok is False
    assert by_id["custom.hidden"].status == "relocated"
    assert by_id["custom.hidden"].observed_path == "notes"
    assert by_id["login.password"].status == "missing"
    assert by_id["login.password"].observed_path is None


def test_wrong_run_is_an_input_error_instead_of_seventeen_false_findings(tmp_path: Path) -> None:
    expected = build_bundle(seed="expected")
    returned = build_bundle(seed="different")
    manifest_path = tmp_path / "manifest.json"
    export_path = tmp_path / "return.json"
    manifest_path.write_text(json.dumps(expected.manifest), encoding="utf-8")
    export_path.write_text(json.dumps(returned.probe), encoding="utf-8")
    manifest = load_manifest(manifest_path)

    with pytest.raises(AuditError, match="no items for run"):
        audit_manifest(manifest, load_export(export_path, title_prefix=manifest.title_prefix))


def test_manifest_rejects_non_synthetic_or_unknown_schema(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "synthetic_data": False,
                "run_id": "run",
                "title_prefix": "VaultCanary run —",
                "features": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(AuditError, match="schema_version"):
        load_manifest(path)


def test_bitwarden_csv_exposes_field_type_and_item_type_losses(tmp_path: Path) -> None:
    bundle = build_bundle(seed="csv-loss")
    login = bundle.probe["items"][0]
    manifest_path = tmp_path / "manifest.json"
    export_path = tmp_path / "return.csv"
    manifest_path.write_text(json.dumps(bundle.manifest), encoding="utf-8")
    with export_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "folder",
                "favorite",
                "type",
                "name",
                "notes",
                "fields",
                "reprompt",
                "login_uri",
                "login_username",
                "login_password",
                "login_totp",
            ]
        )
        writer.writerow(
            [
                bundle.probe["folders"][0]["name"],
                "1",
                "login",
                login["name"],
                login["notes"],
                "\n".join(f"{field['name']}: {field['value']}" for field in login["fields"]),
                "0",
                login["login"]["uris"][0]["uri"],
                login["login"]["username"],
                login["login"]["password"],
                login["login"]["totp"],
            ]
        )
    manifest = load_manifest(manifest_path)

    report = audit_manifest(manifest, load_export(export_path, title_prefix=manifest.title_prefix))
    by_id = {result.feature_id: result for result in report.results}

    assert by_id["custom.hidden"].status == "relocated"
    assert by_id["custom.hidden"].observed_path == "custom.untyped.Canary hidden"
    assert by_id["card.number"].status == "missing"


def test_1pux_string_field_exposes_hidden_field_relocation(tmp_path: Path) -> None:
    bundle = build_bundle(seed="1pux-loss")
    login = bundle.probe["items"][0]
    hidden = next(field for field in login["fields"] if field["name"] == "Canary hidden")
    manifest_path = tmp_path / "manifest.json"
    export_path = tmp_path / "return.1pux"
    manifest_path.write_text(json.dumps(bundle.manifest), encoding="utf-8")
    export_data = {
        "accounts": [
            {
                "vaults": [
                    {
                        "items": [
                            {
                                "categoryUuid": "001",
                                "favIndex": 1,
                                "overview": {"title": login["name"], "urls": []},
                                "details": {
                                    "notesPlain": login["notes"],
                                    "loginFields": [],
                                    "sections": [
                                        {
                                            "fields": [
                                                {
                                                    "id": "hidden",
                                                    "title": "Canary hidden",
                                                    "fieldType": "STRING",
                                                    "value": hidden["value"],
                                                }
                                            ]
                                        }
                                    ],
                                },
                            }
                        ]
                    }
                ]
            }
        ]
    }
    with zipfile.ZipFile(export_path, "w") as archive:
        archive.writestr("export.data", json.dumps(export_data))
    manifest = load_manifest(manifest_path)

    report = audit_manifest(manifest, load_export(export_path, title_prefix=manifest.title_prefix))
    hidden_result = next(
        result for result in report.results if result.feature_id == "custom.hidden"
    )

    assert hidden_result.status == "relocated"
    assert hidden_result.observed_path == "custom.text.Canary hidden"

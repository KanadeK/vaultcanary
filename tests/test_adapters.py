from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

import pytest

from vaultcanary.adapters import ExportError, load_export
from vaultcanary.generate import build_bundle


def test_loads_generated_bitwarden_json_into_semantic_paths(tmp_path: Path) -> None:
    bundle = build_bundle(seed="adapters")
    export_path = tmp_path / "return.json"
    export_path.write_text(json.dumps(bundle.probe), encoding="utf-8")

    vault = load_export(export_path)
    login = vault.by_title[f"VaultCanary {bundle.run_id} — Login"]

    assert vault.format_name == "bitwarden-json"
    assert len(vault.items) == 4
    assert login.values["login.username"] == f"canary+{bundle.run_id}@example.invalid"
    assert login.values["custom.hidden.Canary hidden"].endswith("CUSTOM-HIDDEN")
    assert login.values["folder"].endswith("FOLDER")


def test_loads_bitwarden_csv_and_marks_custom_fields_as_untyped(tmp_path: Path) -> None:
    export_path = tmp_path / "return.csv"
    with export_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "folder": "VCN-run-FOLDER",
                "favorite": "1",
                "type": "login",
                "name": "VaultCanary run — Login",
                "notes": "VCN-run-LOGIN-NOTES",
                "fields": "Canary text: VCN-run-CUSTOM-TEXT\nCanary hidden: VCN-run-CUSTOM-HIDDEN",
                "reprompt": "0",
                "login_uri": "https://login-run.example.invalid/account",
                "login_username": "canary+run@example.invalid",
                "login_password": "VCN!run!PASSWORD!7x",
                "login_totp": "otpauth://totp/VaultCanary:run?secret=AAAA",
            }
        )

    vault = load_export(export_path)
    item = vault.by_title["VaultCanary run — Login"]

    assert vault.format_name == "bitwarden-csv"
    assert item.values["favorite"] is True
    assert item.values["custom.untyped.Canary hidden"] == "VCN-run-CUSTOM-HIDDEN"


def test_loads_1pux_without_extracting_the_archive(tmp_path: Path) -> None:
    export_path = tmp_path / "return.1pux"
    export_data = {
        "accounts": [
            {
                "attrs": {"name": "Test"},
                "vaults": [
                    {
                        "attrs": {"name": "Imported"},
                        "items": [
                            {
                                "favIndex": 1,
                                "categoryUuid": "001",
                                "overview": {
                                    "title": "VaultCanary run — Login",
                                    "urls": [
                                        {
                                            "label": "website",
                                            "url": "https://login-run.example.invalid/account",
                                        }
                                    ],
                                },
                                "details": {
                                    "notesPlain": "VCN-run-LOGIN-NOTES",
                                    "loginFields": [
                                        {
                                            "designation": "username",
                                            "name": "username",
                                            "type": "T",
                                            "value": "canary+run@example.invalid",
                                        },
                                        {
                                            "designation": "password",
                                            "name": "password",
                                            "type": "P",
                                            "value": "VCN!run!PASSWORD!7x",
                                        },
                                    ],
                                    "sections": [
                                        {
                                            "name": "Section_run",
                                            "title": "Canary fields",
                                            "fields": [
                                                {
                                                    "id": "text_run",
                                                    "title": "Canary text",
                                                    "fieldType": "STRING",
                                                    "value": "VCN-run-CUSTOM-TEXT",
                                                },
                                                {
                                                    "id": "hidden_run",
                                                    "title": "Canary hidden",
                                                    "fieldType": "CONCEALED",
                                                    "value": "VCN-run-CUSTOM-HIDDEN",
                                                },
                                                {
                                                    "id": "totp_run",
                                                    "title": "one-time password",
                                                    "fieldType": "OTP",
                                                    "value": "otpauth://totp/VaultCanary:run?secret=AAAA",
                                                },
                                            ],
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                ],
            }
        ]
    }
    with zipfile.ZipFile(export_path, "w") as archive:
        archive.writestr("export.attributes", '{"version": 3}')
        archive.writestr("export.data", json.dumps(export_data))

    vault = load_export(export_path)
    item = vault.by_title["VaultCanary run — Login"]

    assert vault.format_name == "1password-1pux"
    assert item.values["login.uri"] == "https://login-run.example.invalid/account"
    assert item.values["custom.hidden.Canary hidden"] == "VCN-run-CUSTOM-HIDDEN"
    assert item.values["login.totp"].endswith("secret=AAAA")


def test_rejects_encrypted_bitwarden_json(tmp_path: Path) -> None:
    export_path = tmp_path / "encrypted.json"
    export_path.write_text('{"encrypted": true, "items": []}', encoding="utf-8")

    with pytest.raises(ExportError, match="encrypted Bitwarden exports"):
        load_export(export_path)


def test_rejects_1pux_without_export_data(tmp_path: Path) -> None:
    export_path = tmp_path / "broken.1pux"
    with zipfile.ZipFile(export_path, "w") as archive:
        archive.writestr("export.attributes", '{"version": 3}')

    with pytest.raises(ExportError, match=r"export\.data"):
        load_export(export_path)


def test_rejects_input_above_the_size_limit(tmp_path: Path) -> None:
    export_path = tmp_path / "large.json"
    export_path.write_text('{"encrypted": false, "items": []}', encoding="utf-8")

    with pytest.raises(ExportError, match="larger than"):
        load_export(export_path, max_bytes=8)

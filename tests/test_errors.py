from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

import pytest

from vaultcanary.adapters import ExportError, load_export
from vaultcanary.audit import AuditError, audit_manifest, load_manifest
from vaultcanary.cli import main
from vaultcanary.generate import build_bundle, write_bundle
from vaultcanary.model import NormalizedItem, NormalizedVault


def test_export_reader_rejects_missing_and_unsupported_files(tmp_path: Path) -> None:
    with pytest.raises(ExportError, match="cannot read"):
        load_export(tmp_path / "missing.json")

    unsupported = tmp_path / "return.txt"
    unsupported.write_text("not supported", encoding="utf-8")
    with pytest.raises(ExportError, match=r"\.json, \.csv, and \.1pux"):
        load_export(unsupported)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("not json", "valid UTF-8 JSON"),
        ("[]", "root must be an object"),
        ('{"encrypted": false}', "items must be an array"),
        ('{"encrypted": false, "items": {}, "folders": []}', "items must be an array"),
        ('{"encrypted": false, "items": [], "folders": {}}', "folders must be an array"),
    ],
)
def test_bitwarden_json_rejects_malformed_roots(tmp_path: Path, payload: str, message: str) -> None:
    path = tmp_path / "return.json"
    path.write_text(payload, encoding="utf-8")

    with pytest.raises(ExportError, match=message):
        load_export(path)


def test_bitwarden_json_rejects_invalid_item_and_field_types(tmp_path: Path) -> None:
    path = tmp_path / "return.json"
    path.write_text(
        json.dumps(
            {
                "encrypted": False,
                "folders": [],
                "items": [{"name": "Canary", "type": "login", "fields": []}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ExportError, match=r"items\[0\]\.type"):
        load_export(path)

    path.write_text(
        json.dumps(
            {
                "encrypted": False,
                "folders": [],
                "items": [{"name": "Canary", "type": 1, "fields": [{"value": "x"}]}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ExportError, match=r"fields\[0\]\.name"):
        load_export(path)


def test_bitwarden_csv_rejects_unknown_headers_and_missing_names(tmp_path: Path) -> None:
    wrong = tmp_path / "wrong.csv"
    wrong.write_text("name,password\nitem,value\n", encoding="utf-8")
    with pytest.raises(ExportError, match="headers"):
        load_export(wrong)

    missing_name = tmp_path / "missing-name.csv"
    headers = [
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
    with missing_name.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerow({"type": "login", "name": ""})
    with pytest.raises(ExportError, match="has no name"):
        load_export(missing_name)


def test_1pux_rejects_bad_zip_bad_json_and_oversized_member(tmp_path: Path) -> None:
    bad_zip = tmp_path / "bad.1pux"
    bad_zip.write_bytes(b"not a zip")
    with pytest.raises(ExportError, match="valid 1PUX ZIP"):
        load_export(bad_zip)

    bad_json = tmp_path / "bad-json.1pux"
    with zipfile.ZipFile(bad_json, "w") as archive:
        archive.writestr("export.data", "not json")
    with pytest.raises(ExportError, match="valid UTF-8 JSON"):
        load_export(bad_json)

    oversized = tmp_path / "oversized.1pux"
    with zipfile.ZipFile(oversized, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("export.data", " " * 4096)
    with pytest.raises(ExportError, match="larger than"):
        load_export(oversized, max_bytes=1024)

    duplicate = tmp_path / "duplicate.1pux"
    with (
        pytest.warns(UserWarning, match="Duplicate name"),
        zipfile.ZipFile(duplicate, "w") as archive,
    ):
        archive.writestr("export.data", '{"accounts": []}')
        archive.writestr("export.data", '{"accounts": []}')
    with pytest.raises(ExportError, match=r"exactly one export\.data"):
        load_export(duplicate)


def _valid_manifest_payload() -> dict[str, object]:
    return build_bundle(seed="manifest-errors").manifest


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.update(synthetic_data=False), "synthetic_data"),
        (lambda value: value.update(title_prefix="VaultCanary other —"), "title_prefix"),
        (lambda value: value.update(features=[]), "non-empty array"),
        (lambda value: value.update(features=["bad"]), r"features\[0\]"),
    ],
)
def test_manifest_rejects_invalid_contract_shapes(
    tmp_path: Path, mutate: object, message: str
) -> None:
    payload = _valid_manifest_payload()
    mutate(payload)  # type: ignore[operator]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(AuditError, match=message):
        load_manifest(path)


def test_manifest_rejects_duplicate_features_bad_values_and_foreign_items(tmp_path: Path) -> None:
    for label, mutation, message in (
        (
            "duplicate",
            lambda features: features.append(dict(features[0])),
            "duplicate manifest feature_id",
        ),
        (
            "value",
            lambda features: features[0].update(expected_value=123),
            "expected_value",
        ),
        (
            "kind",
            lambda features: features[0].update(kind="guess"),
            "comparison kind",
        ),
        (
            "foreign",
            lambda features: features[0].update(item_title="VaultCanary other — Login"),
            "another run",
        ),
    ):
        payload = _valid_manifest_payload()
        features = payload["features"]
        assert isinstance(features, list)
        mutation(features)
        path = tmp_path / f"{label}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(AuditError, match=message):
            load_manifest(path)


def test_manifest_rejects_terminal_control_characters(tmp_path: Path) -> None:
    payload = _valid_manifest_payload()
    features = payload["features"]
    assert isinstance(features, list)
    features[0]["feature_id"] = "login.\x1b[31mred"
    path = tmp_path / "terminal-control.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(AuditError, match="control characters"):
        load_manifest(path)


def test_audit_rejects_duplicate_canary_titles(tmp_path: Path) -> None:
    bundle = build_bundle(seed="duplicates")
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(bundle.manifest), encoding="utf-8")
    manifest = load_manifest(path)
    title = bundle.probe["items"][0]["name"]
    item = NormalizedItem(title, "login", {"title": title})
    vault = NormalizedVault("test", (item, item))

    with pytest.raises(AuditError, match="duplicate exported item title"):
        audit_manifest(manifest, vault)


def test_generate_refuses_a_nonempty_output_directory(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    output.mkdir()
    (output / "keep.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="not empty"):
        write_bundle(output, seed="no-overwrite")


def test_cli_refuses_report_paths_that_overwrite_inputs(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    assert main(["generate", str(bundle_dir), "--seed", "paths"]) == 0
    manifest = bundle_dir / "vaultcanary-manifest.json"
    returned = bundle_dir / "vaultcanary-bitwarden.json"

    assert main(["audit", str(manifest), str(returned), "--json", str(manifest)]) == 2
    same_report = tmp_path / "same.out"
    assert (
        main(
            [
                "audit",
                str(manifest),
                str(returned),
                "--json",
                str(same_report),
                "--html",
                str(same_report),
            ]
        )
        == 2
    )

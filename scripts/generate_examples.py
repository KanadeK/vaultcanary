"""Generate committed known-good and deliberately lossy example exports."""

from __future__ import annotations

import argparse
import csv
import json
import zipfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from vaultcanary.adapters import load_export
from vaultcanary.audit import audit_manifest, load_manifest
from vaultcanary.generate import build_bundle

SEED = "vaultcanary-v0.1-demo"


def generate_examples(output: Path) -> None:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"example output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    bundle = build_bundle(seed=SEED)
    manifest_path = output / "vaultcanary-manifest.json"
    good_path = output / "known-good-bitwarden.json"
    csv_path = output / "lossy-bitwarden.csv"
    one_pux_path = output / "lossy-1password.1pux"
    _write_json(manifest_path, bundle.manifest)
    _write_json(good_path, bundle.probe)
    _write_lossy_csv(csv_path, bundle.probe)
    _write_lossy_1pux(one_pux_path, bundle.probe)
    (output / "README.md").write_text(_example_readme(), encoding="utf-8", newline="\n")

    manifest = load_manifest(manifest_path)
    good = audit_manifest(manifest, load_export(good_path, title_prefix=manifest.title_prefix))
    csv_report = audit_manifest(manifest, load_export(csv_path, title_prefix=manifest.title_prefix))
    one_pux = audit_manifest(
        manifest, load_export(one_pux_path, title_prefix=manifest.title_prefix)
    )
    if not good.ok or csv_report.ok or one_pux.ok:
        raise RuntimeError("generated example contracts did not produce pass/fail/fail evidence")


def _write_lossy_csv(path: Path, probe: dict[str, Any]) -> None:
    login = probe["items"][0]
    with path.open("w", encoding="utf-8", newline="") as handle:
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
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "folder": probe["folders"][0]["name"],
                "favorite": "1",
                "type": "login",
                "name": login["name"],
                "notes": login["notes"],
                "fields": "\n".join(
                    f"{field['name']}: {field['value']}" for field in login["fields"]
                ),
                "reprompt": "0",
                "login_uri": login["login"]["uris"][0]["uri"],
                "login_username": login["login"]["username"],
                "login_password": login["login"]["password"],
                "login_totp": login["login"]["totp"],
            }
        )


def _write_lossy_1pux(path: Path, probe: dict[str, Any]) -> None:
    login = probe["items"][0]
    fields = [
        {
            "id": field["name"].replace(" ", "_").lower(),
            "title": field["name"],
            "fieldType": "STRING",
            "value": field["value"],
        }
        for field in login["fields"]
    ]
    fields.append(
        {
            "id": "totp",
            "title": "one-time password",
            "fieldType": "OTP",
            "value": login["login"]["totp"],
        }
    )
    export_data = {
        "accounts": [
            {
                "attrs": {"name": "VaultCanary Example"},
                "vaults": [
                    {
                        "attrs": {"name": "Imported"},
                        "items": [
                            {
                                "favIndex": 1,
                                "categoryUuid": "001",
                                "overview": {
                                    "title": login["name"],
                                    "urls": [
                                        {
                                            "label": "website",
                                            "url": login["login"]["uris"][0]["uri"],
                                        }
                                    ],
                                    "tags": [probe["folders"][0]["name"]],
                                },
                                "details": {
                                    "notesPlain": login["notes"],
                                    "loginFields": [
                                        {
                                            "designation": "username",
                                            "name": "username",
                                            "type": "T",
                                            "value": login["login"]["username"],
                                        },
                                        {
                                            "designation": "password",
                                            "name": "password",
                                            "type": "P",
                                            "value": login["login"]["password"],
                                        },
                                    ],
                                    "sections": [{"name": "canary", "fields": fields}],
                                },
                            }
                        ],
                    }
                ],
            }
        ]
    }
    attributes = {"version": 3, "description": "1Password Unencrypted Export"}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _write_zip_member(archive, "export.attributes", attributes)
        _write_zip_member(archive, "export.data", export_data)


def _write_zip_member(archive: zipfile.ZipFile, name: str, value: dict[str, Any]) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _example_readme() -> str:
    return """# VaultCanary examples

All records are synthetic and use reserved `.invalid` network locations.

```console
vaultcanary audit vaultcanary-manifest.json known-good-bitwarden.json
# exit 0: all 17 features preserved

vaultcanary audit vaultcanary-manifest.json lossy-bitwarden.csv
# exit 1: CSV loses item types and custom-field type semantics

vaultcanary audit vaultcanary-manifest.json lossy-1password.1pux
# exit 1: the sample omits non-login item types and relocates field semantics
```

The lossy files are intentionally incomplete test evidence, not exports from or
endorsements of either product.
"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args(argv)
    generate_examples(arguments.output)
    print(f"Generated examples in {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

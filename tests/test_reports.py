from __future__ import annotations

import json
from pathlib import Path

from vaultcanary.adapters import load_export
from vaultcanary.audit import audit_manifest, load_manifest
from vaultcanary.generate import build_bundle
from vaultcanary.reports import render_html, render_json, render_terminal


def test_reports_agree_and_do_not_copy_unrelated_item_values(tmp_path: Path) -> None:
    bundle = build_bundle(seed="redaction")
    bundle.probe["items"].append(
        {
            "type": 1,
            "name": "Real account that must not enter reports",
            "notes": "PRIVATE-NOTE-MUST-NOT-APPEAR",
            "favorite": False,
            "login": {
                "username": "private-user@example.invalid",
                "password": "PRIVATE-PASSWORD-MUST-NOT-APPEAR",
                "totp": None,
                "uris": [],
            },
        }
    )
    manifest_path = tmp_path / "manifest.json"
    export_path = tmp_path / "return.json"
    manifest_path.write_text(json.dumps(bundle.manifest), encoding="utf-8")
    export_path.write_text(json.dumps(bundle.probe), encoding="utf-8")
    manifest = load_manifest(manifest_path)
    report = audit_manifest(manifest, load_export(export_path, title_prefix=manifest.title_prefix))

    terminal = render_terminal(report)
    json_text = render_json(report)
    html_text = render_html(report)
    machine = json.loads(json_text)

    assert machine["summary"] == {
        "missing": 0,
        "preserved": 17,
        "relocated": 0,
        "total": 17,
    }
    assert "17/17 features preserved" in terminal
    assert "VaultCanary migration fidelity" in html_text
    for secret in ("PRIVATE-NOTE-MUST-NOT-APPEAR", "PRIVATE-PASSWORD-MUST-NOT-APPEAR"):
        assert secret not in terminal
        assert secret not in json_text
        assert secret not in html_text


def test_html_escapes_manifest_derived_text(tmp_path: Path) -> None:
    bundle = build_bundle(seed="escaping")
    bundle.manifest["features"][0]["feature_id"] = "login.<script>alert(1)</script>"
    manifest_path = tmp_path / "manifest.json"
    export_path = tmp_path / "return.json"
    manifest_path.write_text(json.dumps(bundle.manifest), encoding="utf-8")
    export_path.write_text(json.dumps(bundle.probe), encoding="utf-8")
    manifest = load_manifest(manifest_path)
    report = audit_manifest(manifest, load_export(export_path, title_prefix=manifest.title_prefix))

    html_text = render_html(report)

    assert "<script>alert(1)</script>" not in html_text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_text

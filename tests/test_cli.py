from __future__ import annotations

import json
from pathlib import Path

from vaultcanary.cli import main


def test_cli_proves_success_and_writes_reports(tmp_path: Path, capsys: object) -> None:
    bundle_dir = tmp_path / "bundle"

    assert main(["generate", str(bundle_dir), "--seed", "cli-good"]) == 0
    assert (
        main(
            [
                "audit",
                str(bundle_dir / "vaultcanary-manifest.json"),
                str(bundle_dir / "vaultcanary-bitwarden.json"),
                "--json",
                str(tmp_path / "report.json"),
                "--html",
                str(tmp_path / "report.html"),
            ]
        )
        == 0
    )
    assert json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))["ok"] is True
    assert "17/17 features preserved" in (tmp_path / "report.html").read_text(encoding="utf-8")


def test_cli_returns_one_for_a_real_fidelity_loss(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    assert main(["generate", str(bundle_dir), "--seed", "cli-loss"]) == 0
    export_path = bundle_dir / "vaultcanary-bitwarden.json"
    export = json.loads(export_path.read_text(encoding="utf-8"))
    export["items"][0]["login"].pop("password")
    export_path.write_text(json.dumps(export), encoding="utf-8")

    assert (
        main(
            [
                "audit",
                str(bundle_dir / "vaultcanary-manifest.json"),
                str(export_path),
            ]
        )
        == 1
    )


def test_cli_returns_two_without_a_traceback_for_bad_input(tmp_path: Path, capsys: object) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")

    assert main(["audit", str(bad), str(bad)]) == 2
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "error:" in captured.err
    assert "Traceback" not in captured.err

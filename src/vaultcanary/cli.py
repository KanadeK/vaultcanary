"""VaultCanary command-line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from vaultcanary import __version__
from vaultcanary.adapters import ExportError, load_export
from vaultcanary.audit import AuditError, audit_manifest, load_manifest
from vaultcanary.generate import write_bundle
from vaultcanary.reports import render_html, render_json, render_terminal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vaultcanary",
        description="Test password-manager migration fidelity with synthetic canaries.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="write a synthetic Bitwarden probe")
    generate.add_argument("output_dir", type=Path)
    generate.add_argument("--seed", help="make output deterministic for demos and tests")

    audit = subparsers.add_parser("audit", help="audit one return export against a manifest")
    audit.add_argument("manifest", type=Path)
    audit.add_argument("return_export", type=Path)
    audit.add_argument("--json", dest="json_path", type=Path)
    audit.add_argument("--html", dest="html_path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "generate":
            written = write_bundle(arguments.output_dir, seed=arguments.seed)
            print(f"Generated synthetic run {written.run_id} in {arguments.output_dir}")
            return 0
        return _run_audit(arguments)
    except (AuditError, ExportError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def _run_audit(arguments: argparse.Namespace) -> int:
    manifest = load_manifest(arguments.manifest)
    vault = load_export(arguments.return_export, title_prefix=manifest.title_prefix)
    report = audit_manifest(manifest, vault)
    _validate_output_paths(
        inputs=(arguments.manifest, arguments.return_export),
        outputs=(arguments.json_path, arguments.html_path),
    )
    print(render_terminal(report), end="")
    if arguments.json_path is not None:
        arguments.json_path.write_text(render_json(report), encoding="utf-8", newline="\n")
    if arguments.html_path is not None:
        arguments.html_path.write_text(render_html(report), encoding="utf-8", newline="\n")
    return 0 if report.ok else 1


def _validate_output_paths(*, inputs: tuple[Path, ...], outputs: tuple[Path | None, ...]) -> None:
    resolved_inputs = {path.resolve() for path in inputs}
    resolved_outputs = [path.resolve() for path in outputs if path is not None]
    if any(path in resolved_inputs for path in resolved_outputs):
        raise AuditError("a report path must not overwrite an input file")
    if len(resolved_outputs) != len(set(resolved_outputs)):
        raise AuditError("JSON and HTML reports must use different paths")

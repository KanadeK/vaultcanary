"""Redacted terminal, JSON, and standalone HTML reports."""

from __future__ import annotations

import html
import json
from typing import Any

from vaultcanary.audit import AuditReport


def report_dict(report: AuditReport) -> dict[str, Any]:
    """Return the stable public report without sentinel or vault values."""

    return {
        "schema_version": 1,
        "tool": "vaultcanary",
        "run_id": report.run_id,
        "return_format": report.format_name,
        "ok": report.ok,
        "summary": {
            "total": len(report.results),
            "preserved": report.preserved_count,
            "relocated": report.relocated_count,
            "missing": report.missing_count,
        },
        "results": [
            {
                "feature_id": result.feature_id,
                "status": result.status,
                "expected_path": result.expected_path,
                "observed_path": result.observed_path,
            }
            for result in report.results
        ],
    }


def render_json(report: AuditReport) -> str:
    return json.dumps(report_dict(report), indent=2, sort_keys=True) + "\n"


def render_terminal(report: AuditReport) -> str:
    verdict = "PASS" if report.ok else "REVIEW"
    lines = [
        f"VaultCanary {report.run_id} / {report.format_name}",
        (
            f"{verdict}: {report.preserved_count}/{len(report.results)} features preserved; "
            f"{report.relocated_count} relocated; {report.missing_count} missing"
        ),
    ]
    for result in report.results:
        location = result.expected_path
        if result.status == "relocated":
            location = f"{result.expected_path} -> {result.observed_path}"
        lines.append(f"{result.status.upper():9} {result.feature_id} [{location}]")
    return "\n".join(lines) + "\n"


def render_html(report: AuditReport) -> str:
    rows = "\n".join(
        (
            f'<tr class="{html.escape(result.status)}">'
            f"<td><code>{html.escape(result.feature_id)}</code></td>"
            f"<td>{html.escape(result.status)}</td>"
            f"<td><code>{html.escape(result.expected_path)}</code></td>"
            f"<td><code>{html.escape(result.observed_path or '—')}</code></td>"
            "</tr>"
        )
        for result in report.results
    )
    verdict = "PASS" if report.ok else "REVIEW"
    summary = (
        f"{report.preserved_count}/{len(report.results)} features preserved; "
        f"{report.relocated_count} relocated; {report.missing_count} missing"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VaultCanary migration fidelity</title>
<style>
:root {{ color-scheme: light dark; font-family: ui-sans-serif, system-ui, sans-serif; }}
body {{ max-width: 72rem; margin: 0 auto; padding: 2rem; line-height: 1.5; }}
.summary {{ border: 2px solid currentColor; border-radius: .8rem; padding: 1rem 1.25rem; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; }}
th, td {{ border-bottom: 1px solid #8888; padding: .65rem; text-align: left; }}
.preserved td:nth-child(2) {{ color: #138a4b; font-weight: 700; }}
.relocated td:nth-child(2), .missing td:nth-child(2) {{ color: #c34f14; font-weight: 700; }}
code {{ overflow-wrap: anywhere; }}
</style>
</head>
<body>
<main>
<h1>VaultCanary migration fidelity</h1>
<section class="summary" aria-label="Audit summary">
<strong>{verdict}</strong>
<p>{html.escape(summary)}</p>
<p>Run <code>{html.escape(report.run_id)}</code> · Return format
<code>{html.escape(report.format_name)}</code></p>
</section>
<table>
<thead><tr><th>Feature</th><th>Status</th><th>Expected field</th>
<th>Observed field</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
<p>This report contains feature identifiers and semantic field paths only. It does not
copy password-manager item values.</p>
</main>
</body>
</html>
"""

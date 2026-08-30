"""Run the complete release-equivalent local gate."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    ".venv",
    ".pytest-tmp",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "release",
}
TEXT_SUFFIXES = {".py", ".md", ".toml", ".yml", ".yaml", ".json", ".txt", ".svg"}
SECRET_PATTERNS = {
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def check(*, skip_package: bool) -> None:
    _assert_version_contract()
    _assert_no_secrets()
    for command in (
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "mypy"],
    ):
        _run(command)
    pytest_temp = Path(tempfile.mkdtemp(prefix=".pytest-run-", dir=ROOT))
    try:
        _run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--basetemp",
                str(pytest_temp / "work"),
            ]
        )
    finally:
        _safe_remove_temp(pytest_temp, ".pytest-run-")
    _run(["uv", "--cache-dir", str(ROOT / ".uv-cache"), "audit", "--locked"])

    manifest = ROOT / "examples" / "vaultcanary-manifest.json"
    _run(
        [
            sys.executable,
            "-m",
            "vaultcanary",
            "audit",
            str(manifest),
            str(ROOT / "examples" / "known-good-bitwarden.json"),
        ]
    )
    for lossy in ("lossy-bitwarden.csv", "lossy-1password.1pux"):
        _run(
            [
                sys.executable,
                "-m",
                "vaultcanary",
                "audit",
                str(manifest),
                str(ROOT / "examples" / lossy),
            ],
            expected=1,
        )

    staging = Path(tempfile.mkdtemp(prefix=".gate-", dir=ROOT))
    try:
        generated_examples = staging / "examples"
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "generate_examples.py"),
                str(generated_examples),
            ]
        )
        _assert_same_files(ROOT / "examples", generated_examples)

        source_bundle = staging / "source-bundle"
        _run(
            [
                sys.executable,
                "-m",
                "vaultcanary",
                "generate",
                str(source_bundle),
                "--seed",
                "release-gate",
            ]
        )
        _run(
            [
                sys.executable,
                "-m",
                "vaultcanary",
                "audit",
                str(source_bundle / "vaultcanary-manifest.json"),
                str(source_bundle / "vaultcanary-bitwarden.json"),
                "--json",
                str(source_bundle / "report.json"),
                "--html",
                str(source_bundle / "report.html"),
            ]
        )
        if skip_package:
            return

        _remove_generated(ROOT / "dist", "dist")
        _remove_generated(ROOT / "release", "release")
        build_environment = dict(os.environ)
        build_environment.update(SOURCE_DATE_EPOCH="1788048000", PYTHONHASHSEED="0")
        _run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--sdist",
                "--outdir",
                str(ROOT / "dist"),
            ],
            env=build_environment,
        )
        distributions = sorted([*(ROOT / "dist").glob("*.whl"), *(ROOT / "dist").glob("*.tar.gz")])
        _run([sys.executable, "-m", "twine", "check", *map(str, distributions)])
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "package_release.py"),
                "--output",
                str(ROOT / "release"),
            ]
        )
        _assert_release_assets()

        environment = staging / "clean-venv"
        _run([sys.executable, "-m", "venv", str(environment)])
        clean_python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        wheel = next((ROOT / "release").glob("vaultcanary-*.whl"))
        _run([str(clean_python), "-m", "pip", "install", "--no-deps", str(wheel)])
        executable = environment / (
            "Scripts/vaultcanary.exe" if os.name == "nt" else "bin/vaultcanary"
        )
        wheel_bundle = staging / "wheel-bundle"
        _run([str(executable), "generate", str(wheel_bundle), "--seed", "wheel-gate"])
        _run(
            [
                str(executable),
                "audit",
                str(wheel_bundle / "vaultcanary-manifest.json"),
                str(wheel_bundle / "vaultcanary-bitwarden.json"),
            ]
        )
    finally:
        _safe_remove_staging(staging)


def _run(command: list[str], *, expected: int = 0, env: dict[str, str] | None = None) -> None:
    print(f"\n$ {' '.join(command)}", flush=True)
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(completed.stdout, end="")
    if completed.returncode != expected:
        raise RuntimeError(
            f"command exited {completed.returncode}; expected {expected}: {' '.join(command)}"
        )


def _assert_version_contract() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]
    if not isinstance(version, str):
        raise RuntimeError("project version must be a string")
    source = (ROOT / "src" / "vaultcanary" / "__init__.py").read_text(encoding="utf-8")
    if f'__version__ = "{version}"' not in source:
        raise RuntimeError("package version does not match pyproject.toml")
    if f"## [{version}]" not in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"):
        raise RuntimeError("CHANGELOG does not contain the package version")
    if not (ROOT / "release-notes" / f"v{version}.md").is_file():
        raise RuntimeError("release notes do not match the package version")


def _assert_no_secrets() -> None:
    findings: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(ROOT)
        if any(part in SKIP_DIRS or part.startswith(".gate-") for part in relative.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{relative}: possible {label}")
    if findings:
        raise RuntimeError("secret scan failed:\n" + "\n".join(findings))


def _assert_same_files(expected: Path, actual: Path) -> None:
    expected_files = {path.name: path.read_bytes() for path in expected.iterdir() if path.is_file()}
    actual_files = {path.name: path.read_bytes() for path in actual.iterdir() if path.is_file()}
    if expected_files != actual_files:
        raise RuntimeError("committed examples do not match deterministic regeneration")


def _assert_release_assets() -> None:
    names = {path.name for path in (ROOT / "release").iterdir() if path.is_file()}
    required_fragments = (".whl", ".tar.gz", "-examples.zip", "SHA256SUMS.txt")
    for fragment in required_fragments:
        if not any(name.endswith(fragment) for name in names):
            raise RuntimeError(f"release asset missing: *{fragment}")


def _remove_generated(path: Path, expected_name: str) -> None:
    resolved = path.resolve()
    if resolved.parent != ROOT.resolve() or resolved.name != expected_name:
        raise RuntimeError(f"refusing to remove unexpected generated path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _safe_remove_staging(path: Path) -> None:
    resolved = path.resolve()
    if resolved.parent != ROOT.resolve() or not resolved.name.startswith(".gate-"):
        raise RuntimeError(f"refusing to remove unexpected staging path: {resolved}")
    shutil.rmtree(resolved)


def _safe_remove_temp(path: Path, prefix: str) -> None:
    resolved = path.resolve()
    if resolved.parent != ROOT.resolve() or not resolved.name.startswith(prefix):
        raise RuntimeError(f"refusing to remove unexpected temporary path: {resolved}")
    shutil.rmtree(resolved)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-package", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        check(skip_package=arguments.skip_package)
    except RuntimeError as error:
        print(f"\nGATE FAILED: {error}", file=sys.stderr)
        return 1
    print("\nVAULTCANARY_RELEASE_GATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

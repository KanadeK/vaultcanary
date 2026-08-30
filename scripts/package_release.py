"""Assemble GitHub Release assets from verified distributions and examples."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import zipfile
from collections.abc import Sequence
from pathlib import Path

from vaultcanary import __version__

ROOT = Path(__file__).resolve().parents[1]


def package_release(output: Path) -> tuple[Path, ...]:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"release output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    distributions = sorted([*(ROOT / "dist").glob("*.whl"), *(ROOT / "dist").glob("*.tar.gz")])
    if len(distributions) != 2:
        raise RuntimeError("expected exactly one wheel and one source distribution in dist")
    assets: list[Path] = []
    for distribution in distributions:
        destination = output / distribution.name
        shutil.copyfile(distribution, destination)
        assets.append(destination)

    example_zip = output / f"vaultcanary-{__version__}-examples.zip"
    with zipfile.ZipFile(example_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sorted((ROOT / "examples").iterdir()):
            if source.is_file():
                info = zipfile.ZipInfo(
                    f"vaultcanary-{__version__}-examples/{source.name}",
                    date_time=(1980, 1, 1, 0, 0, 0),
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, source.read_bytes())
    assets.append(example_zip)

    checksums = output / "SHA256SUMS.txt"
    checksums.write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in sorted(assets)),
        encoding="utf-8",
        newline="\n",
    )
    assets.append(checksums)
    return tuple(assets)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "release")
    arguments = parser.parse_args(argv)
    assets = package_release(arguments.output)
    for asset in assets:
        print(asset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Zip a built app folder for distribution, splitting it into parts under GitHub's 2 GB asset limit.

Usage: python tools/package_release.py <app_folder> <output.zip> [--part-size-mb 1900]

Split parts are named <output.zip>.001, .002, ... Users rejoin them with 7-Zip (open the .001 file)
or with: copy /b AutoGuardian.zip.001+AutoGuardian.zip.002 AutoGuardian.zip
"""

from __future__ import annotations

import argparse
import os
import zipfile
from pathlib import Path


def make_zip(app_dir: Path, zip_path: Path) -> None:
    root_name = app_dir.name
    outputs_dir = app_dir / "outputs"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zf:
        for path in sorted(app_dir.rglob("*")):
            arcname = Path(root_name) / path.relative_to(app_dir)
            # outputs/ ships as empty folders: never package data from a local test run (DB, logs, captures)
            in_outputs = outputs_dir in path.parents
            if path.is_dir():
                if in_outputs or not any(path.iterdir()):
                    zf.writestr(str(arcname).replace(os.sep, "/") + "/", "")
            elif not in_outputs:
                zf.write(path, arcname)


def split_file(path: Path, part_size: int) -> list[Path]:
    parts: list[Path] = []
    with open(path, "rb") as src:
        index = 1
        while True:
            chunk_path = path.with_name(f"{path.name}.{index:03d}")
            written = 0
            with open(chunk_path, "wb") as dst:
                while written < part_size:
                    block = src.read(min(64 * 1024 * 1024, part_size - written))
                    if not block:
                        break
                    dst.write(block)
                    written += len(block)
            if written == 0:
                chunk_path.unlink()
                break
            parts.append(chunk_path)
            index += 1
    return parts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_dir", type=Path)
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--part-size-mb", type=int, default=1900)
    args = parser.parse_args()

    zip_path: Path = args.zip_path
    for old in [zip_path, *zip_path.parent.glob(zip_path.name + ".[0-9][0-9][0-9]")]:
        old.unlink(missing_ok=True)

    make_zip(args.app_dir, zip_path)
    size = zip_path.stat().st_size
    part_size = args.part_size_mb * 1024 * 1024
    print(f"{zip_path}: {size / 1024**2:.0f} MB")

    if size > part_size:
        parts = split_file(zip_path, part_size)
        zip_path.unlink()
        for p in parts:
            print(f"  {p}: {p.stat().st_size / 1024**2:.0f} MB")


if __name__ == "__main__":
    main()

"""Generate manifest.json for the AutoGuardian launcher.

The launcher downloads https://github.com/<repo>/releases/latest/download/manifest.json and then
the package files listed in it (URL, size, SHA-256), choosing the GPU or CPU variant.

Usage:
    python tools/make_manifest.py --app-version 1.1.0 --tag v1.1.0 --out dist/manifest.json
    python tools/make_manifest.py ... --base-url http://localhost:8000   # local testing
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO = "NguyenMinhPhuc/pro-dem-va-tinh-van-toc"
VARIANTS = {
    "cuda": ("GPU NVIDIA (CUDA) + CPU", "AutoGuardian-win64-cuda.zip", "cuda"),
    "cpu": ("Chỉ CPU (nhẹ)", "AutoGuardian-win64.zip", "cpu"),
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(16 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


def package_files(dist: Path, zip_name: str) -> list[Path]:
    """Single zip, or its split parts .001, .002, ... in order."""
    single = dist / zip_name
    if single.exists():
        return [single]
    return sorted(dist.glob(zip_name + ".[0-9][0-9][0-9]"))


def dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-version", required=True)
    parser.add_argument("--tag", required=True, help="Release tag hosting the package files")
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--out", type=Path, default=Path("dist/manifest.json"))
    parser.add_argument("--base-url", help="Override download URL prefix (default: GitHub release of --tag)")
    args = parser.parse_args()

    base_url = (args.base_url or f"https://github.com/{REPO}/releases/download/{args.tag}").rstrip("/")
    manifest = {"app_version": args.app_version, "variants": {}}

    for key, (label, zip_name, dist_sub) in VARIANTS.items():
        files = package_files(args.dist, zip_name)
        app_dir = args.dist / dist_sub / "AutoGuardian"
        if not files or not app_dir.exists():
            print(f"skip {key}: package or {app_dir} missing")
            continue
        manifest["variants"][key] = {
            "label": label,
            "unpacked_size": dir_size(app_dir),
            "files": [
                {"name": f.name, "url": f"{base_url}/{f.name}", "size": f.stat().st_size, "sha256": sha256_of(f)}
                for f in files
            ],
        }
        print(f"{key}: {[f.name for f in files]}")

    args.out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()

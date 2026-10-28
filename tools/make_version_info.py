"""Write a PyInstaller --version-file so the .exe carries product name / version metadata.

SignPath Foundation requires product name and version on every signed binary; the same values
are enforced by .signpath/artifact-configuration.xml.

Usage: python tools/make_version_info.py <version> <exe_name> <description> <output_file>
"""

from __future__ import annotations

import re
import sys

PRODUCT_NAME = "AutoGuardian"
COMPANY = "AutoGuardian Team"
COPYRIGHT = "Copyright (c) 2026 Nguyen Minh Phuc. MIT License."

TEMPLATE = """# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0, OS=0x40004,
    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', {company!r}),
      StringStruct('FileDescription', {description!r}),
      StringStruct('FileVersion', {version!r}),
      StringStruct('InternalName', {internal!r}),
      StringStruct('LegalCopyright', {copyright!r}),
      StringStruct('OriginalFilename', {exe_name!r}),
      StringStruct('ProductName', {product!r}),
      StringStruct('ProductVersion', {version!r})])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> None:
    version, exe_name, description, output = sys.argv[1:5]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"Version must be MAJOR.MINOR.PATCH, got {version!r}")
    nums = tuple(int(p) for p in version.split(".")) + (0,)
    with open(output, "w", encoding="utf-8") as f:
        f.write(TEMPLATE.format(
            nums=nums, version=version, company=COMPANY, description=description,
            internal=exe_name.rsplit(".", 1)[0], copyright=COPYRIGHT, exe_name=exe_name, product=PRODUCT_NAME,
        ))


if __name__ == "__main__":
    main()

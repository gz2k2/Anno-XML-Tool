"""Build the Windows one-file executable locally with PyInstaller.

Usage:
    python build_onefile.py
    python build_onefile.py --clean
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_version() -> str:
    version_file = ROOT / "version.txt"
    return version_file.read_text(encoding="utf-8").strip() if version_file.exists() else "0.0.0"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Anno XML Viewer as a PyInstaller one-file executable")
    parser.add_argument("--clean", action="store_true", help="Remove the PyInstaller work directory before building")
    args = parser.parse_args()

    version = read_version()
    name = f"Anno_XML_Viewer_v{version}"
    command = [
        sys.executable,
        "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--icon", str(ROOT / "data" / "ui" / "AnnoXMLTool.ico"),
        "--name", name,
        "--add-data", f"{ROOT / 'data' / 'ui' / 'kofi5.webp'};data/ui",
        "--add-data", f"{ROOT / 'version.txt'};.",
        "--add-data", f"{ROOT / 'data' / 'ui' / 'AnnoXMLTool.ico'};data/ui",
    ]
    if args.clean:
        command.append("--clean")
    command.append(str(ROOT / "Anno_XML_Viewer.py"))

    print("Building:")
    print(" ".join(f'"{part}"' if " " in part else part for part in command))
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode == 0:
        print(f"\nBuild complete: {ROOT / 'dist' / (name + '.exe')}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

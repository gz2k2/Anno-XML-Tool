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


def qt_themes_installed() -> bool:
    """True when qt-themes can be collected into the build."""
    try:
        import importlib.util
        return importlib.util.find_spec("qt_themes") is not None
    except Exception:
        return False


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

    # qt-themes stores its colour schemes as *.json data files inside the
    # package. PyInstaller ignores package data unless it is collected
    # explicitly, which would leave the theme selector with only the built-in
    # entry.
    if qt_themes_installed():
        command += [
            "--collect-data", "qt_themes",
            "--hidden-import", "qt_themes",
        ]
        print("qt-themes found - theme files will be bundled.")
    else:
        print("WARNING: qt-themes is not installed, the build will only offer "
              "the built-in theme. Install it with: pip install qt-themes")

    # qt-themes prefers qtpy/PySide over PyQt6. theme_manager installs a qtpy
    # shim at runtime, so these must not be dragged into the build - a second
    # Qt binding would bloat the executable and can clash with PyQt6.
    for module in ("PySide6", "PySide2", "qtpy", "shiboken6", "shiboken2"):
        command += ["--exclude-module", module]

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

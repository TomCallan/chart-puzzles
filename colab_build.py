#!/usr/bin/env python3
"""Build the puzzle book on a Colab VM.

Designed for the Colab CLI. Either:

    # interactive session (upload the project first)
    colab --auth adc new --gpu T4 --session book
    colab --auth adc upload chart-puzzles.tar.gz /content/chart-puzzles.tar.gz -s book
    colab --auth adc exec -s book -f colab_build.py
    colab --auth adc download /content/trading-puzzle-book/output/workbook.pdf ./workbook.pdf -s book
    colab --auth adc stop -s book

    # or one-shot (fresh VM, auto-released; project is cloned from GitHub)
    colab --auth adc run --gpu T4 colab_build.py

Set REPO_URL to override the clone source, or place the project at
/content/trading-puzzle-book (or a chart-puzzles.tar.gz in /content).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(os.environ.get("PROJECT_DIR", "/content/trading-puzzle-book"))
TARBALL = Path(os.environ.get("TARBALL", "/content/chart-puzzles.tar.gz"))
REPO_URL = os.environ.get("REPO_URL", "https://github.com/TomCallan/chart-puzzles.git")

APT_PACKAGES = (
    "libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2 "
    "libgdk-pixbuf-2.0-0 libharfbuzz-subset0"
)


def sh(command: str, check: bool = True) -> None:
    print(f"\n$ {command}", flush=True)
    subprocess.run(command, shell=True, check=check)


def ensure_project() -> None:
    if PROJECT.exists():
        return
    if TARBALL.exists():
        sh(f"mkdir -p {PROJECT.parent} && tar -xzf {TARBALL} -C {PROJECT.parent}")
        return
    print(f"Cloning {REPO_URL} ...")
    sh(f"git clone --depth 1 {REPO_URL} {PROJECT}")
    if not PROJECT.exists():
        sys.exit("Could not obtain the project: upload a tarball or set REPO_URL.")


def main() -> int:
    sh(f"apt-get -qq update && apt-get -qq install -y {APT_PACKAGES}")
    ensure_project()
    sh(f"pip install -q -r {PROJECT}/requirements.txt")
    sh(f"cd {PROJECT} && python generate_charts.py")
    sh(f"cd {PROJECT} && python build_pdf.py")
    sh(f"cd {PROJECT} && python make_catalog.py")

    print("\n=== Done ===")
    for path in (
        PROJECT / "output/workbook.pdf",
        PROJECT / "output/answer_key.pdf",
        PROJECT / "build/catalog.json",
        PROJECT / "CATALOG.md",
    ):
        print(f"  {path}  ({'ok' if path.exists() else 'MISSING'})")
    print(
        "\nDownload with:\n"
        f"  colab --auth adc download {PROJECT}/output/workbook.pdf ./workbook.pdf -s <session>\n"
        f"  colab --auth adc download {PROJECT}/build/catalog.json ./catalog.json -s <session>"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

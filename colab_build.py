#!/usr/bin/env python3
"""Run the full pattern detection on a Colab VM and push the results back.

What it does:
  1. installs the system + Python dependencies
  2. clones the repo (HTTPS by default; SSH if REPO_URL starts with git@)
  3. runs generate_charts.py -> build_pdf.py -> make_catalog.py
  4. commits the refreshed catalog (README.md + CATALOG.md) and pushes to GitHub

Usage:
    colab --auth adc new --session book
    GITHUB_TOKEN=<pat> colab --auth adc exec -s book -f colab_build.py
    colab --auth adc stop -s book

The token needs write access to the repo contents (classic PAT `repo` scope, or
a fine-grained token with Contents: read and write). Without GITHUB_TOKEN the
build still runs and the driver tells you how to download the catalog instead.

Environment overrides:
    GITHUB_TOKEN     PAT used for the push (HTTPS)
    REPO_URL         clone URL (default https://github.com/TomCallan/chart-puzzles.git)
    PROJECT_DIR      where to put the checkout (default /content/trading-puzzle-book)
    TARBALL          optional tarball to unpack instead of cloning
    GIT_SSH_KEY      private key path for an SSH clone (default /content/deploy_key)
    COMMIT_OUTPUTS   set to 1 to also commit output/*.pdf
    COMMIT_MESSAGE   commit message (default includes the run summary)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(os.environ.get("PROJECT_DIR", "/content/trading-puzzle-book"))
TARBALL = Path(os.environ.get("TARBALL", "/content/chart-puzzles.tar.gz"))
REPO_URL = os.environ.get(
    "REPO_URL", "https://github.com/TomCallan/chart-puzzles.git"
)
SSH_KEY = os.environ.get("GIT_SSH_KEY", "/content/deploy_key")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
COMMIT_OUTPUTS = os.environ.get("COMMIT_OUTPUTS", "0") == "1"
GIT_NAME = os.environ.get("GIT_NAME", "Howard Hughes")
GIT_EMAIL = os.environ.get("GIT_EMAIL", "howard.hughes@users.noreply.github.com")

APT_PACKAGES = (
    "libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2 "
    "libgdk-pixbuf-2.0-0 libharfbuzz-subset0"
)


def sh(command: str, check: bool = True) -> None:
    shown = command.replace(GITHUB_TOKEN, "***") if GITHUB_TOKEN else command
    print(f"\n$ {shown}", flush=True)
    subprocess.run(command, shell=True, check=check)


def setup_ssh() -> None:
    key = Path(SSH_KEY)
    if not key.exists():
        sys.exit(f"SSH key not found at {key}. Upload it or set GIT_SSH_KEY.")
    sh("mkdir -p ~/.ssh && chmod 700 ~/.ssh")
    sh(f"cp {key} ~/.ssh/id_ed25519 && chmod 600 ~/.ssh/id_ed25519")
    sh("ssh-keyscan -t ed25519,rsa github.com >> ~/.ssh/known_hosts 2>/dev/null || true")
    sh(
        'git config --global core.sshCommand '
        '"ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"'
    )
    sh("ssh -T git@github.com || true")


def ensure_project() -> None:
    if PROJECT.exists():
        return
    if TARBALL.exists():
        sh(f"mkdir -p {PROJECT.parent} && tar -xzf {TARBALL} -C {PROJECT.parent}")
        return
    if REPO_URL.startswith("git@"):
        setup_ssh()
    sh(f"git clone --depth 1 {REPO_URL} {PROJECT}", check=False)
    if not PROJECT.exists():
        sys.exit("Clone failed. Set REPO_URL, upload a tarball, or add a deploy key.")


def build() -> None:
    sh(f"apt-get -qq update && apt-get -qq install -y {APT_PACKAGES}")
    ensure_project()
    sh(f"pip install -q -r {PROJECT}/requirements.txt")
    sh(f"cd {PROJECT} && python generate_charts.py")
    sh(f"cd {PROJECT} && python build_pdf.py")
    sh(f"cd {PROJECT} && python make_catalog.py")
    if (PROJECT / "make_review.py").exists():
        sh(f"cd {PROJECT} && python make_review.py", check=False)


def summarise() -> str:
    import json

    catalog = PROJECT / "build" / "catalog.json"
    if not catalog.exists():
        return "Update catalog from Colab run"
    data = json.loads(catalog.read_text())
    questions = data.get("questions", {})
    clues = data.get("clues", {})
    short = [
        name
        for name, stat in data.get("patterns", {}).items()
        if stat.get("hits_available", 0) < 12
    ]
    return (
        "Refresh catalog from full detection run\n\n"
        f"- {data.get('selected', 0)} puzzles selected, "
        f"{data.get('totals', {}).get('hits_available', 0)} winning examples available\n"
        f"- questions: {questions}\n"
        f"- clues: {clues}\n"
        f"- patterns below 12 hits: {len(short)}"
    )


def push() -> None:
    if not GITHUB_TOKEN:
        print(
            "\nNo GITHUB_TOKEN set, so nothing was pushed. Download the results:\n"
            f"  colab --auth adc download {PROJECT}/build/catalog.json ./catalog.json -s <session>\n"
            f"  colab --auth adc download {PROJECT}/CATALOG.md ./CATALOG.md -s <session>"
        )
        return

    remote = "github.com/TomCallan/chart-puzzles.git"
    sh(f'cd {PROJECT} && git config user.name "{GIT_NAME}"')
    sh(f'cd {PROJECT} && git config user.email "{GIT_EMAIL}"')
    sh(f"cd {PROJECT} && git remote set-url origin https://{GITHUB_TOKEN}@{remote}")
    sh(f"cd {PROJECT} && git add -A README.md CATALOG.md config.yaml", check=False)
    if COMMIT_OUTPUTS:
        sh(
            f"cd {PROJECT} && git add -f output/workbook.pdf output/answer_key.pdf",
            check=False,
        )

    staged = subprocess.run(
        f"cd {PROJECT} && git diff --cached --quiet",
        shell=True,
    ).returncode
    if staged == 0:
        print("\nNo catalog changes to commit.")
        return

    message = os.environ.get("COMMIT_MESSAGE") or summarise()
    subprocess.run(
        ["git", "-C", str(PROJECT), "commit", "-m", message], check=True
    )
    sh(f"cd {PROJECT} && git push origin HEAD:main")
    print("\nPushed the refreshed catalog to main.")


def main() -> int:
    build()
    print("\n=== Done ===")
    for path in (
        PROJECT / "output/workbook.pdf",
        PROJECT / "build/catalog.json",
        PROJECT / "CATALOG.md",
    ):
        print(f"  {path}  ({'ok' if path.exists() else 'MISSING'})")
    push()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

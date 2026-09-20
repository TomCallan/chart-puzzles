#!/usr/bin/env python3
"""Build the puzzle book on a Colab VM.

Designed for the Colab CLI. Three ways to get the project onto the VM, in
order of preference for a private repo:

1. Upload a tarball (no git access needed at all)
   colab --auth adc new --gpu T4 --session book
   colab --auth adc upload chart-puzzles.tar.gz /content/chart-puzzles.tar.gz -s book
   colab --auth adc exec -s book -f colab_build.py

2. SSH deploy key (private repo, read-only key)
   ssh-keygen -t ed25519 -f ~/.ssh/chart-puzzles-deploy -N ""
   # add ~/.ssh/chart-puzzles-deploy.pub as a *Deploy Key* (read-only) on GitHub
   colab --auth adc upload ~/.ssh/chart-puzzles-deploy /content/deploy_key -s book
   colab --auth adc exec -s book -f colab_build.py

3. HTTPS token
   REPO_URL=https://<token>@github.com/TomCallan/chart-puzzles.git \
     colab --auth adc exec -s book -f colab_build.py

One-shot (fresh VM, auto-released) also works:
   colab --auth adc run --gpu T4 colab_build.py

Environment overrides: PROJECT_DIR, TARBALL, REPO_URL, GIT_SSH_KEY.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(os.environ.get("PROJECT_DIR", "/content/trading-puzzle-book"))
TARBALL = Path(os.environ.get("TARBALL", "/content/chart-puzzles.tar.gz"))
REPO_URL = os.environ.get("REPO_URL", "git@github.com:TomCallan/chart-puzzles.git")
SSH_KEY = os.environ.get("GIT_SSH_KEY", "/content/deploy_key")

APT_PACKAGES = (
    "libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2 "
    "libgdk-pixbuf-2.0-0 libharfbuzz-subset0"
)


def sh(command: str, check: bool = True) -> None:
    print(f"\n$ {command}", flush=True)
    subprocess.run(command, shell=True, check=check)


def setup_ssh() -> None:
    """Install the uploaded private key and trust github.com."""
    key = Path(SSH_KEY)
    if not key.exists():
        sys.exit(
            f"SSH key not found at {key}. Upload it (colab upload ...) or set "
            "GIT_SSH_KEY. Alternatively upload a tarball to skip git entirely."
        )
    sh("mkdir -p ~/.ssh && chmod 700 ~/.ssh")
    sh(f"cp {key} ~/.ssh/id_ed25519 && chmod 600 ~/.ssh/id_ed25519")
    sh("ssh-keyscan -t ed25519,rsa github.com >> ~/.ssh/known_hosts 2>/dev/null || true")
    sh(
        'git config --global core.sshCommand '
        '"ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"'
    )
    print("Testing GitHub SSH access ...", flush=True)
    sh("ssh -T git@github.com || true")


def ensure_project() -> None:
    if PROJECT.exists():
        return
    if TARBALL.exists():
        sh(f"mkdir -p {PROJECT.parent} && tar -xzf {TARBALL} -C {PROJECT.parent}")
        return
    if REPO_URL.startswith("git@"):
        setup_ssh()
    print(f"Cloning {REPO_URL} ...", flush=True)
    sh(f"git clone --depth 1 {REPO_URL} {PROJECT}", check=False)
    if not PROJECT.exists():
        sys.exit(
            "Clone failed. Upload a tarball, add a read-only deploy key, or set "
            "REPO_URL to an HTTPS URL with a token."
        )


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

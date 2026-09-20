#!/usr/bin/env python3
"""Serve the review directory over HTTP with caching disabled.

Keeps iterative review from showing stale HTML after a rebuild.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import os
from pathlib import Path


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:  # quieter logs
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--dir", default="public")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    directory = (root / args.dir).resolve()
    handler = functools.partial(NoCacheHandler, directory=str(directory))
    with http.server.ThreadingHTTPServer((args.bind, args.port), handler) as httpd:
        print(f"serving {directory} on http://{args.bind}:{args.port}")
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

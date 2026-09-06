#!/usr/bin/env python3
"""Download (or verify) the binaries listed under "remote_binary" in package.json.

The binaries are not committed to git (they are ~360 MB). This script rebuilds
``bin/`` from the same URLs and SHA-256 hashes the Decky store uses, so a clone
can be packaged into an installable zip with ``scripts/package.sh``.

    python3 scripts/fetch-bin.py            # download missing / mismatching files
    python3 scripts/fetch-bin.py --verify   # only check hashes, exit 1 on mismatch
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = ROOT / "bin"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path) -> None:
    """Stream ``url`` to ``dest``; falls back to curl when Python has no usable CA
    bundle (python.org builds on macOS), which does not affect SteamOS."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "decky-framegen-fetch-bin"})
        with urllib.request.urlopen(request) as response, open(tmp, "wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if total:
                    sys.stdout.write(f"\r  {dest.name}: {done * 100 // total:3d}%")
                    sys.stdout.flush()
        sys.stdout.write("\n")
    except urllib.error.URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc) or not shutil.which("curl"):
            raise
        print(f"  urllib cannot verify TLS here ({exc.reason}); using curl")
        subprocess.run(["curl", "-fsSL", "--retry", "3", "-o", str(tmp), url], check=True)
    tmp.replace(dest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verify", action="store_true", help="only verify existing files, never download")
    args = parser.parse_args()

    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    entries = package.get("remote_binary") or []
    if not entries:
        print("package.json has no remote_binary entries", file=sys.stderr)
        return 1

    BIN_DIR.mkdir(exist_ok=True)
    failures = 0
    for entry in entries:
        name, url, expected = entry["name"], entry["url"], entry["sha256hash"].lower()
        dest = BIN_DIR / name
        if dest.exists() and sha256_of(dest) == expected:
            print(f"ok       {name}")
            continue
        if args.verify:
            print(f"MISMATCH {name} ({'missing' if not dest.exists() else 'sha256 differs'})")
            failures += 1
            continue
        print(f"fetch    {name}\n  {url}")
        download(url, dest)
        actual = sha256_of(dest)
        if actual != expected:
            print(f"MISMATCH {name}: expected {expected}, got {actual}", file=sys.stderr)
            dest.unlink()
            failures += 1
        else:
            print(f"ok       {name}")

    if failures:
        print(f"{failures} file(s) failed", file=sys.stderr)
        return 1
    print("all bundled binaries match package.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

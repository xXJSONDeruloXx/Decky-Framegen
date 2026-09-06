#!/usr/bin/env python3
"""Refresh the OptiScaler v10 injector from a newer upstream nightly.

    python3 scripts/refresh-injector.py                 # inspect the latest nightly
    python3 scripts/refresh-injector.py nightly-20260912 # inspect a specific tag
    python3 scripts/refresh-injector.py --apply         # also update main.py / package.json / bin

Steps: download the nightly 7z from optiscaler/OptiScaler-nightly, extract its root
OptiScaler.dll (7z/7zz/bsdtar), read the version banner, check that the DLL still
contains every INI key the plugin relies on, print the hashes, and with --apply
rewrite OPTISCALER_V10_ARCHIVE_ASSET / OPTISCALER_V10_INJECTOR in main.py, the
remote_binary entry in package.json and the file in bin/. The old archive's URL is
kept pointing at the previous mirror until you upload the new one (the script tells
you the exact upload command). Run the test suite afterwards.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NIGHTLY_API = "https://api.github.com/repos/optiscaler/OptiScaler-nightly/releases/{tag}"
# INI keys the plugin writes for the v10 runtime; a nightly that dropped one of them
# would silently change behaviour on the Deck.
REQUIRED_STRINGS = ["LoadCustomAmdxc64OnRdna2", "Fsr4ForceModel", "FGInput", "FGOutput", "nukems", "LoadAsiPlugins", "UseHQFont", "OptiDllPath"]
BANNER = re.compile(rb"OptiScaler v([0-9][0-9A-Za-z.\-]*) \(([0-9a-f]{8})\) \((\d{8}_\d{6})\)")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tls_unusable(exc: Exception) -> bool:
    return "CERTIFICATE_VERIFY_FAILED" in str(exc) and shutil.which("curl") is not None


def fetch_json(url: str) -> dict:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "decky-framegen-refresh", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.URLError as exc:
        if not _tls_unusable(exc):
            raise
        out = subprocess.run(["curl", "-fsSL", "-H", "Accept: application/vnd.github+json", url], check=True, capture_output=True, text=True)
        return json.loads(out.stdout)


def download(url: str, dest: Path) -> None:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "decky-framegen-refresh"})
        with urllib.request.urlopen(request) as response, open(dest, "wb") as out:
            shutil.copyfileobj(response, out)
    except urllib.error.URLError as exc:
        if not _tls_unusable(exc):
            raise
        subprocess.run(["curl", "-fsSL", "--retry", "3", "-o", str(dest), url], check=True)


def extract_member(archive: Path, member: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    for tool in ("7z", "7zz", "7za"):
        if shutil.which(tool):
            cmd = [tool, "x", "-y", "-o" + str(out_dir), str(archive), member]
            break
    else:
        if not shutil.which("bsdtar"):
            raise RuntimeError("need 7z, 7zz, 7za or bsdtar")
        cmd = ["bsdtar", "-xf", str(archive), "-C", str(out_dir), member]
    subprocess.run(cmd, check=True, capture_output=True)
    extracted = out_dir / member
    if not extracted.exists():
        raise RuntimeError(f"{member} not found in {archive.name}")
    return extracted


def inspect_dll(dll: Path) -> dict:
    data = dll.read_bytes()
    match = BANNER.search(data)
    if not match:
        raise RuntimeError("no 'OptiScaler vX (hash) (date)' banner found in the DLL")
    version, commit, stamp = (m.decode() for m in match.groups())
    missing = [s for s in REQUIRED_STRINGS if s.encode() not in data]
    return {"version": version, "commit": commit, "stamp": stamp, "sha256": sha256_of(dll), "missing": missing}


def apply_update(archive_name: str, archive_sha: str, injector_sha: str, version_label: str, archive_path: Path) -> None:
    main_py = ROOT / "main.py"
    text = main_py.read_text(encoding="utf-8")
    text, n1 = re.subn(
        r'(OPTISCALER_V10_ARCHIVE_ASSET = \{\s*"name": ")[^"]+(",\s*"sha256": ")[0-9a-f]{64}(",\s*"version": ")[^"]+(")',
        lambda m: f"{m.group(1)}{archive_name}{m.group(2)}{archive_sha}{m.group(3)}{version_label}{m.group(4)}",
        text, count=1, flags=re.S,
    )
    text, n2 = re.subn(
        r'(OPTISCALER_V10_INJECTOR = \{\s*"name": "OptiScaler\.dll",\s*"sha256": ")[0-9a-f]{64}(")',
        lambda m: f"{m.group(1)}{injector_sha}{m.group(2)}", text, count=1, flags=re.S,
    )
    if n1 != 1 or n2 != 1:
        raise RuntimeError("could not locate the injector constants in main.py")
    main_py.write_text(text, encoding="utf-8")

    package_json = ROOT / "package.json"
    package = json.loads(package_json.read_text(encoding="utf-8"))
    entry = next(e for e in package["remote_binary"] if e["name"].startswith("OptiScaler_v10"))
    old_name = entry["name"]
    entry["name"] = archive_name
    entry["sha256hash"] = archive_sha
    entry["url"] = entry["url"].rsplit("/", 1)[0] + "/" + archive_name  # same host; upload the new asset there
    package_json.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")

    bin_dir = ROOT / "bin"
    bin_dir.mkdir(exist_ok=True)
    shutil.copy2(archive_path, bin_dir / archive_name)
    if old_name != archive_name and (bin_dir / old_name).exists():
        (bin_dir / old_name).unlink()
    print(f"updated main.py, package.json and bin/{archive_name}")
    print("next: upload the archive so the URL in package.json resolves, e.g.")
    print(f"  gh release create optiscaler-{archive_name.split('_')[-1].split('.')[0]} bin/{archive_name} -R <owner>/Decky-Framegen-bins")
    print("then bump BUNDLE_LAYOUT_VERSION is NOT needed (the fingerprint includes the new hashes) and run the tests.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tag", nargs="?", default="latest", help="nightly tag, default: latest")
    parser.add_argument("--apply", action="store_true", help="rewrite main.py, package.json and bin/")
    args = parser.parse_args()

    if args.tag == "latest":
        # /releases/latest ignores pre-releases, which every nightly is; take the newest entry.
        releases = fetch_json(NIGHTLY_API.format(tag="") .rstrip("/") + "?per_page=1")
        release = releases[0] if isinstance(releases, list) and releases else {}
    else:
        release = fetch_json(NIGHTLY_API.format(tag=f"tags/{args.tag}"))
    asset = next((a for a in release.get("assets", []) if a["name"].endswith(".7z")), None)
    if not asset:
        print("no .7z asset in that release", file=sys.stderr)
        return 1
    print(f"release {release.get('tag_name')}: {asset['name']} ({asset['size']} bytes)")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        archive = tmp_path / asset["name"]
        download(asset["browser_download_url"], archive)
        archive_sha = sha256_of(archive)
        dll = extract_member(archive, "OptiScaler.dll", tmp_path / "x")
        info = inspect_dll(dll)
        print(f"archive sha256: {archive_sha}")
        print(f"injector: OptiScaler v{info['version']} ({info['commit']}) ({info['stamp']}) sha256 {info['sha256']}")
        if info["missing"]:
            print(f"REFUSING: the DLL no longer contains {info['missing']}", file=sys.stderr)
            return 2
        print("all required INI keys present")
        if args.apply:
            version_label = f"v{info['version']}.{info['stamp'].split('_')[0]} ({info['commit']})"
            apply_update(asset["name"], archive_sha, info["sha256"], version_label, archive)
    return 0


if __name__ == "__main__":
    sys.exit(main())

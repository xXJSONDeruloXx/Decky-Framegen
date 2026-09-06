#!/usr/bin/env bash
# Build the installable Decky zip (same layout the decky CLI produces):
#   Decky-Framegen/{plugin.json,package.json,main.py,README.md,LICENSE,dist/,bin/,assets/}
# Usage: scripts/package.sh [output-dir]   (default: ../ next to the repo)
#
# The zip is deliberately named exactly "<plugin name>.zip" (Decky-Framegen.zip).
# Decky Loader derives the plugin name for a file/URL install from the zip filename
# (minus .zip) BEFORE it reads plugin.json, and only uninstalls an existing plugin of
# that name. A versioned filename would overlay the old install instead of replacing
# it (decky-loader backend/decky_loader/browser.py, _install: isInstalled check).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
name="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["name"])' "$root/plugin.json")"
version="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' "$root/package.json")"
out_dir="${1:-$(dirname "$root")}"
# Create it and make it absolute: the zip is written from inside the staging dir.
out_dir="$(mkdir -p "$out_dir" && cd "$out_dir" && pwd)"
out="$out_dir/${name}.zip"
echo "packaging $name v$version"

# Source checkouts keep the launcher scripts under defaults/assets (decky CLI layout);
# release layouts have them under assets/. Either works.
assets_dir="$root/assets"
[[ -f "$assets_dir/fgmod.sh" ]] || assets_dir="$root/defaults/assets"
for required in plugin.json package.json main.py dist/index.js bin; do
  [[ -e "$root/$required" ]] || { echo "missing $required (run 'pnpm run build' and 'python3 scripts/fetch-bin.py' first)" >&2; exit 1; }
done
[[ -f "$assets_dir/fgmod.sh" ]] || { echo "missing assets/fgmod.sh" >&2; exit 1; }
python3 "$root/scripts/fetch-bin.py" --verify >/dev/null || { echo "bin/ does not match package.json remote_binary hashes" >&2; exit 1; }

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/$name"
cp "$root/plugin.json" "$root/package.json" "$root/main.py" "$root/README.md" "$root/LICENSE" "$stage/$name/"
cp -R "$root/dist" "$root/bin" "$stage/$name/"
mkdir -p "$stage/$name/assets"
cp -R "$assets_dir/." "$stage/$name/assets/"
# Banner/icon PNGs live in assets/ in both layouts.
cp "$root"/assets/*.png "$stage/$name/assets/" 2>/dev/null || true
find "$stage" -name .DS_Store -delete
find "$stage" -name __pycache__ -type d -prune -exec rm -rf {} +
chmod +x "$stage/$name/bin/"* "$stage/$name/assets/"*.sh 2>/dev/null || true

rm -f "$out"
(cd "$stage" && zip -qr -X "$out" "$name")
echo "wrote $out"
unzip -l "$out" | awk 'NR>3 && $4 ~ /^[^\/]+\/[^\/]*$/ {print "  " $4}'

"""Shared test harness: stub the ``decky`` module the way Decky Loader's sandbox
does (``sys.modules['decky']``), point HOME at a temp dir, and import ``main``.

Import this module first in every test file so all of them share one ``main``
module bound to one temp HOME (a second ``import main`` would otherwise return
the cached module bound to another file's stub).
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import sys
import tempfile
import types
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent
TEMP_HOME = Path(tempfile.mkdtemp(prefix="fgmod-test-home-"))

# Runtime layout is <plugin>/assets and <plugin>/bin. A source checkout keeps the
# scripts under defaults/assets (the decky CLI moves them to the root at build
# time), so stage a plugin dir with symlinks when needed.
ASSETS_DIR = PLUGIN_DIR / "assets" if (PLUGIN_DIR / "assets" / "fgmod.sh").exists() else PLUGIN_DIR / "defaults" / "assets"
if ASSETS_DIR == PLUGIN_DIR / "assets":
    RUNTIME_PLUGIN_DIR = PLUGIN_DIR
else:
    RUNTIME_PLUGIN_DIR = Path(tempfile.mkdtemp(prefix="fgmod-test-plugin-"))
    (RUNTIME_PLUGIN_DIR / "assets").symlink_to(ASSETS_DIR)
    (RUNTIME_PLUGIN_DIR / "bin").symlink_to(PLUGIN_DIR / "bin")

if "decky" not in sys.modules:
    _decky = types.ModuleType("decky")
    _decky.logger = logging.getLogger("decky-test")
    _decky.DECKY_PLUGIN_DIR = str(RUNTIME_PLUGIN_DIR)
    _decky.HOME = str(TEMP_HOME)
    sys.modules["decky"] = _decky
else:
    TEMP_HOME = Path(sys.modules["decky"].HOME)

if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

import main  # noqa: E402


def reset_home() -> Path:
    """Wipe and recreate the shared temp HOME (call from setUpClass)."""
    shutil.rmtree(TEMP_HOME, ignore_errors=True)
    TEMP_HOME.mkdir(parents=True, exist_ok=True)
    return TEMP_HOME


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ini_value(ini: Path, section: str, key: str) -> str | None:
    """Return the value of ``key`` inside ``[section]`` (first match), or None."""
    current = None
    for raw in ini.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            continue
        if current == section and "=" in line and not line.startswith(";"):
            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.strip()
    return None


__all__ = ["PLUGIN_DIR", "ASSETS_DIR", "TEMP_HOME", "main", "reset_home", "sha256", "ini_value"]

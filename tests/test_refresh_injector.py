"""Offline tests for scripts/refresh-injector.py (no network: fake DLL bytes and a
scratch copy of main.py / package.json)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_DIR / "scripts" / "refresh-injector.py"


def load_script(root: Path):
    spec = importlib.util.spec_from_file_location("refresh_injector", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = root
    return module


class RefreshInjectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="refresh-"))
        shutil.copy2(PLUGIN_DIR / "main.py", self.tmp / "main.py")
        shutil.copy2(PLUGIN_DIR / "package.json", self.tmp / "package.json")
        self.mod = load_script(self.tmp)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _fake_dll(self, *, drop: str | None = None) -> Path:
        body = b"\x00" * 64 + b"OptiScaler v10.0.0-dev (abcdef12) (20260912_080000)\x00"
        for key in self.mod.REQUIRED_STRINGS:
            if key != drop:
                body += key.encode() + b"\x00"
        dll = self.tmp / "OptiScaler.dll"
        dll.write_bytes(body)
        return dll

    def test_inspect_reads_banner_and_checks_keys(self):
        info = self.mod.inspect_dll(self._fake_dll())
        self.assertEqual((info["version"], info["commit"], info["stamp"]), ("10.0.0-dev", "abcdef12", "20260912_080000"))
        self.assertEqual(info["missing"], [])
        self.assertEqual(self.mod.inspect_dll(self._fake_dll(drop="Fsr4ForceModel"))["missing"], ["Fsr4ForceModel"])

    def test_apply_rewrites_constants_and_package_entry(self):
        archive = self.tmp / "OptiScaler_v10.0.0-pre1_20260912.7z"
        archive.write_bytes(b"not a real archive")
        archive_sha = hashlib.sha256(b"not a real archive").hexdigest()
        injector_sha = "1" * 64
        self.mod.apply_update(archive.name, archive_sha, injector_sha, "v10.0.0-dev.20260912 (abcdef12)", archive)

        main_text = (self.tmp / "main.py").read_text(encoding="utf-8")
        self.assertIn(f'"name": "{archive.name}"', main_text)
        self.assertIn(f'"sha256": "{archive_sha}"', main_text)
        self.assertIn('"version": "v10.0.0-dev.20260912 (abcdef12)"', main_text)
        self.assertIn(f'"sha256": "{injector_sha}"', main_text)
        self.assertNotIn("c5f06953d91f01593b1e44273dccb76326aa3725f92eb32e7aebe114383e927e", main_text)
        # The rewritten module must still import and expose consistent constants.
        namespace: dict = {}
        code = main_text.split("class Plugin:")[0]
        import types, sys
        stub = types.ModuleType("decky"); stub.HOME = str(self.tmp); stub.DECKY_PLUGIN_DIR = str(self.tmp)
        import logging; stub.logger = logging.getLogger("x")
        sys.modules.setdefault("decky", stub)
        exec(compile(code, "main-head", "exec"), namespace)
        self.assertEqual(namespace["OPTISCALER_V10_INJECTOR"]["sha256"], injector_sha)
        self.assertEqual(namespace["OPTISCALER_V10_ARCHIVE_ASSET"]["name"], archive.name)

        package = json.loads((self.tmp / "package.json").read_text(encoding="utf-8"))
        entry = next(e for e in package["remote_binary"] if e["name"] == archive.name)
        self.assertEqual(entry["sha256hash"], archive_sha)
        self.assertTrue(entry["url"].endswith("/" + archive.name))
        self.assertTrue((self.tmp / "bin" / archive.name).exists())


if __name__ == "__main__":
    unittest.main()

"""Guards for the shipped frontend bundle and the packaging metadata.

There is no JS test harness; these checks make sure the bundle that ends up in
the zip was rebuilt after the source changes, and that package.json /
plugin.json / main.py agree with each other.

    python3 -m unittest discover -s tests -t tests -v
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from _harness import PLUGIN_DIR, main, sha256

DIST = PLUGIN_DIR / "dist" / "index.js"
TSC = PLUGIN_DIR / "node_modules" / ".bin" / "tsc"


@unittest.skipUnless(DIST.exists(), "dist/index.js not built (run `pnpm run build`)")
class BundleTests(unittest.TestCase):
    def test_bundle_is_an_es_module_built_from_current_sources(self):
        bundle = DIST.read_text(encoding="utf-8")
        self.assertIn("export { index as default };", bundle, "not an ES-module bundle (@decky/rollup output)")
        for needle in [
            "View Details",                 # ResultDisplay is actually rendered now
            "useQuickAccessVisible",        # poll / game-list gating
            "No Steam games found",
            "DLL=",                         # Copy Patch Command honours the proxy DLL
            "Update OptiScaler bundle",     # stale ~/fgmod notice
            "NavigateToExternalWeb",
            "Could not read this game",     # launch-option read failure aborts the patch
            "press the Patch button",       # updated instructions
            "rdna2-valve-411-pre10",
        ]:
            self.assertIn(needle, bundle, f"dist/index.js is stale: missing {needle!r}")
        self.assertNotIn("for the standard direct launch-options method", bundle)

    def test_every_frontend_callable_exists_on_the_backend(self):
        bundle = DIST.read_text(encoding="utf-8")
        names = set(re.findall(r'callable\("(\w+)"\)', bundle))
        source = (PLUGIN_DIR / "src" / "api" / "index.ts").read_text(encoding="utf-8")
        declared = set(re.findall(r'>\("(\w+)"\)', source))
        self.assertTrue(names, "no callable() names found in the bundle")
        self.assertEqual(names, declared, "bundle and src/api/index.ts disagree: dist is stale or the regex missed a name")
        for name in names:
            method = getattr(main.Plugin, name, None)
            self.assertIsNotNone(method, f"frontend calls {name} but main.Plugin has no such method")

    @unittest.skipUnless(TSC.exists(), "node_modules not installed")
    def test_typecheck_passes(self):
        result = subprocess.run([str(TSC), "--noEmit", "-p", "tsconfig.json"], cwd=PLUGIN_DIR, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class PackagingMetadataTests(unittest.TestCase):
    def test_package_json_remote_binaries_match_bin_and_main_py(self):
        package = json.loads((PLUGIN_DIR / "package.json").read_text(encoding="utf-8"))
        entries = package["remote_binary"]
        self.assertEqual(len(entries), 7)
        expected = {
            main.OPTISCALER_ARCHIVE_ASSET["name"]: main.OPTISCALER_ARCHIVE_ASSET["sha256"],
            main.FSR4_INT8_ASSET["name"]: main.FSR4_INT8_ASSET["sha256"],
            main.FSR4_OFFICIAL_411_ASSET["name"]: main.FSR4_OFFICIAL_411_ASSET["sha256"],
            main.AMDXC64_RDNA2_ASSET["name"]: main.AMDXC64_RDNA2_ASSET["sha256"],
            main.FSR4_VALVE_411_ASSET["name"]: main.FSR4_VALVE_411_ASSET["sha256"],
            main.OPTISCALER_V10_ARCHIVE_ASSET["name"]: main.OPTISCALER_V10_ARCHIVE_ASSET["sha256"],
            main.OPTIPATCHER_ASSET["name"]: main.OPTIPATCHER_ASSET["sha256"],
        }
        for entry in entries:
            self.assertIn(entry["name"], expected)
            self.assertEqual(entry["sha256hash"].lower(), expected[entry["name"]].lower(), entry["name"])
            self.assertTrue(entry["url"].startswith("https://github.com/"), entry["url"])
            bundled = PLUGIN_DIR / "bin" / entry["name"]
            if bundled.exists():  # bin/ is not committed; verify when present
                self.assertEqual(sha256(bundled), entry["sha256hash"].lower(), entry["name"])
        self.assertEqual(package["version"], "0.18")
        plugin = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["name"], "Decky-Framegen")
        self.assertEqual(plugin["api_version"], 1)
        self.assertEqual(plugin["flags"], [])

    @unittest.skipUnless(shutil.which("bash"), "bash not available")
    def test_package_script_names_the_zip_after_the_plugin(self):
        script = (PLUGIN_DIR / "scripts" / "package.sh").read_text(encoding="utf-8")
        self.assertIn('out="$out_dir/${name}.zip"', script)


if __name__ == "__main__":
    unittest.main()

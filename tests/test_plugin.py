"""End-to-end checks for the backend against the real bundled binaries.

Runs without Decky: a stub ``decky`` module is injected, HOME is redirected to a
temp dir, and the plugin's own ``bin/`` assets are used. Needs ``7z`` or
``bsdtar`` on PATH (SteamOS and macOS both have bsdtar).

    python3 -m unittest tests/test_plugin.py -v
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
import unittest
from pathlib import Path

from _harness import TEMP_HOME, main, reset_home, sha256, ini_value  # noqa: F401

VALVE = "rdna2-valve-411-pre10"


class InstallAndPatchTests(unittest.TestCase):
    plugin: main.Plugin
    fgmod: Path

    @classmethod
    def setUpClass(cls) -> None:
        reset_home()
        cls.plugin = main.Plugin()
        cls.fgmod = TEMP_HOME / "fgmod"
        result = asyncio.run(cls.plugin.extract_static_optiscaler(VALVE))
        assert result["status"] == "success", result

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEMP_HOME, ignore_errors=True)

    # ── bundle preparation ──────────────────────────────────────────────────

    def test_valve_variant_uses_v10_nightly_injector(self):
        variant_dir = self.fgmod / main.FSR4_VARIANTS[VALVE]["dir_name"]
        injector = variant_dir / "OptiScaler.dll"
        self.assertTrue(injector.exists())
        self.assertEqual(sha256(injector), main.OPTISCALER_V10_INJECTOR["sha256"])
        # Only the injector is taken from the nightly archive; nothing else leaks in.
        self.assertFalse((variant_dir / "OptiScaler").exists())
        self.assertFalse((variant_dir / "OptiScaler.ini").exists())
        for proxy in main.PROXY_DLL_BACKUPS:
            self.assertEqual(sha256(variant_dir / "renames" / proxy), main.OPTISCALER_V10_INJECTOR["sha256"])

    def test_other_variants_keep_the_094_injector(self):
        base = sha256(self.fgmod / "OptiScaler.dll")
        self.assertNotEqual(base, main.OPTISCALER_V10_INJECTOR["sha256"])
        self.assertEqual(sha256(self.fgmod / "renames" / "dxgi.dll"), base)
        for variant_id in ("rdna23-int8", "rdna4-native", "rdna34-official-411", "rdna2-valve-411-094"):
            self.assertIsNone(self.plugin._fsr4_variant_injector_path(self.fgmod, variant_id))

    def test_manifest_and_path_check(self):
        manifest = self.plugin._load_install_manifest(self.fgmod)
        self.assertEqual(manifest["selected_default_variant"], VALVE)
        injector = manifest["fsr4_variants"][VALVE]["injector"]
        self.assertEqual(injector["sha256"], main.OPTISCALER_V10_INJECTOR["sha256"])
        self.assertEqual(injector["source_asset_name"], main.OPTISCALER_V10_ARCHIVE_ASSET["name"])
        status = asyncio.run(self.plugin.check_fgmod_path())
        self.assertTrue(status["exists"], status)
        self.assertEqual(status["selected_fsr4_variant"], VALVE)

    # ── patching a game directory ───────────────────────────────────────────

    def _fake_game(self) -> Path:
        game = Path(tempfile.mkdtemp(prefix="game-", dir=TEMP_HOME))
        (game / "Game.exe").write_bytes(b"MZ")
        return game

    def test_patch_valve_variant_then_switch_then_unpatch(self):
        game = self._fake_game()

        result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(sha256(game / "dxgi.dll"), main.OPTISCALER_V10_INJECTOR["sha256"])
        self.assertEqual(sha256(game / "amdxcffx64.dll"), main.FSR4_VALVE_411_ASSET["sha256"])
        self.assertEqual(sha256(game / "amdxc64.dll"), main.AMDXC64_RDNA2_ASSET["sha256"])
        self.assertEqual(sha256(game / "amd_fidelityfx_upscaler_dx12.dll"), main.FSR4_VARIANTS[VALVE]["sha256"])
        self.assertTrue((game / "plugins" / "OptiPatcher.asi").exists())
        self.assertTrue((game / "D3D12_Optiscaler" / "D3D12Core.dll").exists())
        ini = game / "OptiScaler.ini"
        self.assertEqual(ini_value(ini, "FSR", "Fsr4ForceModel"), "2")
        self.assertEqual(ini_value(ini, "Plugins", "LoadCustomAmdxc64OnRdna2"), "true")
        self.assertEqual(ini_value(ini, "FrameGen", "FGInput"), "nukems")
        self.assertEqual(ini_value(ini, "Menu", "UseHQFont"), "false")
        self.assertEqual(self.plugin._detect_fsr4_variant(game, sha256(game / "amd_fidelityfx_upscaler_dx12.dll")), VALVE)

        # Simulate the marker patch_game() writes, then switch runtime: overrides
        # must be reset and the RDNA2-only DLLs removed.
        self.plugin._write_marker(
            game / main.MARKER_FILENAME,
            appid="1", game_name="Fake", dll_name="dxgi.dll", target_dir=game,
            original_launch_options="", backed_up_files=[], fsr4_variant=VALVE,
        )
        result = self.plugin._manual_patch_directory_impl(
            game, "dxgi.dll", "rdna4-native", allow_managed_support_cleanup=True
        )
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(sha256(game / "dxgi.dll"), sha256(self.fgmod / "OptiScaler.dll"))
        self.assertFalse((game / "amdxc64.dll").exists())
        self.assertFalse((game / "amdxcffx64.dll").exists())
        self.assertFalse((game / "amdxc64.dll.b").exists(), "managed file must not be backed up as an original")
        self.assertEqual(ini_value(ini, "FSR", "Fsr4ForceModel"), "auto")
        self.assertEqual(ini_value(ini, "Plugins", "LoadCustomAmdxc64OnRdna2"), "false")

        result = self.plugin._manual_unpatch_directory_impl(game)
        self.assertEqual(result["status"], "success", result)
        leftovers = sorted(p.name for p in game.iterdir())
        # The shared unpatch keeps the marker: it stores the user's original launch
        # options, which only unpatch_game (with an app id) can hand back to Steam.
        self.assertEqual(leftovers, ["FRAMEGEN_PATCH", "Game.exe"])

    def test_preexisting_game_dxgi_is_backed_up_and_restored(self):
        game = self._fake_game()
        (game / "dxgi.dll").write_bytes(b"original game dxgi")
        result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual((game / "dxgi.dll.b").read_bytes(), b"original game dxgi")
        self.plugin._manual_unpatch_directory_impl(game)
        self.assertEqual((game / "dxgi.dll").read_bytes(), b"original game dxgi")
        self.assertFalse((game / "dxgi.dll.b").exists())


class ExtractCommandTests(unittest.TestCase):
    def test_prefers_7z_then_falls_back_to_bsdtar(self):
        plugin = main.Plugin()
        archive, out = Path("/a/x.7z"), Path("/o")
        original = shutil.which
        try:
            shutil.which = lambda tool: "/usr/bin/7z" if tool == "7z" else None
            self.assertEqual(plugin._archive_extract_command(archive, out, ["OptiScaler.dll"])[:2], ["7z", "x"])
            shutil.which = lambda tool: "/usr/bin/bsdtar" if tool == "bsdtar" else None
            cmd = plugin._archive_extract_command(archive, out, ["OptiScaler.dll"])
            self.assertEqual(cmd, ["bsdtar", "-xf", str(archive), "-C", str(out), "OptiScaler.dll"])
            shutil.which = lambda tool: None
            with self.assertRaises(RuntimeError):
                plugin._archive_extract_command(archive, out, [])
        finally:
            shutil.which = original


if __name__ == "__main__":
    unittest.main()

"""Regression tests for the v0.18 data-safety and compatibility fixes.

Each test corresponds to a finding that survived adversarial review (see
tasks/steamdeck-verification.md). All run against the real bundled binaries.

    python3 -m unittest discover -s tests -t tests -v
"""

from __future__ import annotations

import ast
import asyncio
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _harness import PLUGIN_DIR, TEMP_HOME, main, reset_home, sha256, ini_value

VALVE = "rdna2-valve-411-pre10"


def hashlib_sha256(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()
XESS_FILES = ["libxess.dll", "libxess_dx11.dll", "libxess_fg.dll", "libxell.dll"]


class QuickWinTests(unittest.TestCase):
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

    def _game(self, **files: bytes) -> Path:
        game = Path(tempfile.mkdtemp(prefix="game-", dir=TEMP_HOME))
        (game / "Game.exe").write_bytes(b"MZ")
        for name, content in files.items():
            (game / name).write_bytes(content)
        return game

    def _marker(self, game: Path, variant: str = VALVE, dll_name: str = "dxgi.dll") -> None:
        self.plugin._write_marker(
            game / main.MARKER_FILENAME,
            appid="1", game_name="Fake", dll_name=dll_name, target_dir=game,
            original_launch_options="", backed_up_files=[], fsr4_variant=variant,
        )

    # ── data safety ────────────────────────────────────────────────────────

    def test_game_shipped_xess_dlls_are_backed_up_and_restored(self):
        game = self._game(**{name: b"game " + name.encode() for name in XESS_FILES})
        result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
        self.assertEqual(result["status"], "success", result)
        for name in XESS_FILES:
            self.assertEqual((game / f"{name}.b").read_bytes(), b"game " + name.encode())
            self.assertEqual(sha256(game / name), sha256(self.fgmod / name))

        # Re-patch (runtime switch): the bundle's copies are recognised as managed,
        # the game's backups stay untouched.
        self._marker(game)
        result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", "rdna4-native", allow_managed_support_cleanup=True)
        self.assertEqual(result["status"], "success", result)
        for name in XESS_FILES:
            self.assertEqual((game / f"{name}.b").read_bytes(), b"game " + name.encode())

        self.plugin._manual_unpatch_directory_impl(game)
        for name in XESS_FILES:
            self.assertEqual((game / name).read_bytes(), b"game " + name.encode())
            self.assertFalse((game / f"{name}.b").exists())

    def test_unpatch_keeps_user_asi_mods_and_removes_only_optipatcher(self):
        game = self._game()
        self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
        self.assertTrue((game / "plugins" / "OptiPatcher.asi").exists())
        (game / "plugins" / "UserMod.asi").write_bytes(b"user")
        (game / "plugins" / "cyber_engine_tweaks").mkdir()
        (game / "plugins" / "cyber_engine_tweaks" / "config.json").write_text("{}")

        self.plugin._manual_unpatch_directory_impl(game)
        self.assertFalse((game / "plugins" / "OptiPatcher.asi").exists())
        self.assertEqual((game / "plugins" / "UserMod.asi").read_bytes(), b"user")
        self.assertTrue((game / "plugins" / "cyber_engine_tweaks" / "config.json").exists())

    def test_unpatch_removes_empty_plugins_dir(self):
        game = self._game()
        self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
        self.plugin._manual_unpatch_directory_impl(game)
        self.assertFalse((game / "plugins").exists())

    def test_manual_unpatch_refuses_never_patched_dir(self):
        game = self._game(**{
            "libxess.dll": b"intel", "dbghelp.dll": b"ms", "dxgi.dll": b"reshade",
            "version.dll": b"cet", "nvapi64.dll": b"nv",
        })
        (game / "plugins").mkdir()
        (game / "plugins" / "mod.asi").write_bytes(b"mod")
        before = {p.relative_to(game): p.read_bytes() for p in game.rglob("*") if p.is_file()}

        result = asyncio.run(self.plugin.manual_unpatch_directory(str(game)))
        self.assertEqual(result["status"], "error", result)
        self.assertIn("No Framegen/OptiScaler patch found", result["message"])
        after = {p.relative_to(game): p.read_bytes() for p in game.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_manual_unpatch_accepts_patched_and_backup_only_dirs(self):
        patched = self._game()
        self.plugin._manual_patch_directory_impl(patched, "dxgi.dll", VALVE)
        self.assertEqual(asyncio.run(self.plugin.manual_unpatch_directory(str(patched)))["status"], "success")

        # A patch that only left a backup behind (aborted mid-way) is still unpatchable.
        backup_only = self._game(**{"dxgi.dll.b": b"original"})
        self.assertEqual(asyncio.run(self.plugin.manual_unpatch_directory(str(backup_only)))["status"], "success")
        self.assertEqual((backup_only / "dxgi.dll").read_bytes(), b"original")

    def test_repatch_without_marker_does_not_backup_managed_dlls(self):
        for variant in main.FSR4_VARIANTS:
            with self.subTest(variant=variant):
                game = self._game(**{"amd_fidelityfx_dx12.dll": b"GAME ORIGINAL"})
                for _ in range(2):
                    result = asyncio.run(self.plugin.manual_patch_directory(str(game), "dxgi.dll", variant))
                    self.assertEqual(result["status"], "success", result)
                backups = sorted(p.name for p in game.iterdir() if p.name.endswith(".b"))
                self.assertEqual(backups, ["amd_fidelityfx_dx12.dll.b"])
                asyncio.run(self.plugin.manual_unpatch_directory(str(game)))
                self.assertEqual(sorted(p.name for p in game.iterdir()), ["Game.exe", "amd_fidelityfx_dx12.dll"])
                self.assertEqual((game / "amd_fidelityfx_dx12.dll").read_bytes(), b"GAME ORIGINAL")

    def test_user_placed_driver_dlls_are_backed_up_and_restored(self):
        game = self._game(**{"amdxcffx64.dll": b"user driver", "amdxc64.dll": b"user amdxc"})
        result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual((game / "amdxcffx64.dll.b").read_bytes(), b"user driver")
        self.assertEqual((game / "amdxc64.dll.b").read_bytes(), b"user amdxc")
        self.assertEqual(sha256(game / "amdxcffx64.dll"), main.FSR4_VALVE_411_ASSET["sha256"])

        self._marker(game)
        result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", "rdna4-native", allow_managed_support_cleanup=True)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual((game / "amdxcffx64.dll.b").read_bytes(), b"user driver")
        self.assertFalse((game / "amdxcffx64.dll").exists())

        self.plugin._manual_unpatch_directory_impl(game)
        self.assertEqual((game / "amdxcffx64.dll").read_bytes(), b"user driver")
        self.assertEqual((game / "amdxc64.dll").read_bytes(), b"user amdxc")

    def test_game_shipped_d3dcompiler_is_left_in_place_and_legacy_backup_restored(self):
        game = self._game(**{"d3dcompiler_47.dll": b"ms compiler"})
        self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
        self.assertEqual((game / "d3dcompiler_47.dll").read_bytes(), b"ms compiler")
        self.assertFalse((game / "d3dcompiler_47.dll.b").exists())

        # A v0.17 patch left only the ".b": the next patch (and unpatch) put it back.
        legacy = self._game(**{"d3dcompiler_47.dll.b": b"v017 backup"})
        self.plugin._manual_patch_directory_impl(legacy, "dxgi.dll", VALVE)
        self.assertEqual((legacy / "d3dcompiler_47.dll").read_bytes(), b"v017 backup")
        self.assertFalse((legacy / "d3dcompiler_47.dll.b").exists())
        self.plugin._manual_unpatch_directory_impl(legacy)
        self.assertEqual((legacy / "d3dcompiler_47.dll").read_bytes(), b"v017 backup")

    # ── OptiScaler v10 <-> 0.9.4 INI vocabulary ────────────────────────────

    def test_v10_fg_keys_are_mapped_back_when_leaving_the_valve_runtime(self):
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=repr(newline)):
                game = self._game()
                self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
                ini = game / "OptiScaler.ini"
                text = ini.read_text(encoding="utf-8")
                text = text.replace("FGInput=nukems", "FGInput=NvngxFG").replace("FGOutput=nukems", "FGOutput=auto")
                text = text.replace("[FrameGen]", "[FrameGen]" + newline + "FGNvngxReplacement=Nukems", 1)
                ini.write_text(text, encoding="utf-8", newline=newline)
                self.assertTrue(self.plugin._needs_v10_fg_downgrade(ini))

                self._marker(game)
                result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", "rdna4-native", allow_managed_support_cleanup=True)
                self.assertEqual(result["status"], "success", result)
                self.assertEqual(ini_value(ini, "FrameGen", "FGInput"), "nukems")
                self.assertEqual(ini_value(ini, "FrameGen", "FGOutput"), "nukems")
                self.assertEqual(ini_value(ini, "FrameGen", "FGNvngxReplacement"), "Nukems")

    def test_v10_fg_keys_are_left_alone_for_other_replacements_and_for_valve(self):
        game = self._game()
        self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
        ini = game / "OptiScaler.ini"
        text = ini.read_text(encoding="utf-8").replace("FGInput=nukems", "FGInput=NvngxFG")
        text = text.replace("[FrameGen]", "[FrameGen]\nFGNvngxReplacement=Arturs", 1)
        ini.write_text(text, encoding="utf-8")
        self.assertFalse(self.plugin._needs_v10_fg_downgrade(ini))
        self._marker(game)
        self.plugin._manual_patch_directory_impl(game, "dxgi.dll", "rdna4-native", allow_managed_support_cleanup=True)
        self.assertEqual(ini_value(ini, "FrameGen", "FGInput"), "NvngxFG")

        # Re-patching with the Valve runtime never rewrites v10 spelling.
        game2 = self._game()
        self.plugin._manual_patch_directory_impl(game2, "dxgi.dll", VALVE)
        ini2 = game2 / "OptiScaler.ini"
        ini2.write_text(ini2.read_text(encoding="utf-8").replace("FGInput=nukems", "FGInput=NvngxFG"), encoding="utf-8")
        self._marker(game2)
        self.plugin._manual_patch_directory_impl(game2, "dxgi.dll", VALVE, allow_managed_support_cleanup=True)
        self.assertEqual(ini_value(ini2, "FrameGen", "FGInput"), "NvngxFG")

    def test_foreign_proxy_dlls_survive_reinstall(self):
        """A version.dll/winmm.dll mod loader added after the patch must be backed up
        on Reinstall, while the proxy the plugin manages is replaced silently."""
        game = self._game()
        self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
        self._marker(game, dll_name="dxgi.dll")
        (game / "version.dll").write_bytes(b"CET loader")
        (game / "winmm.dll").write_bytes(b"ASI loader")

        result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", "rdna4-native", allow_managed_support_cleanup=True)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual((game / "version.dll.b").read_bytes(), b"CET loader")
        self.assertEqual((game / "winmm.dll.b").read_bytes(), b"ASI loader")
        self.assertFalse((game / "dxgi.dll.b").exists(), "our own v10 proxy must not be backed up as an original")
        self.assertEqual(sha256(game / "dxgi.dll"), sha256(self.fgmod / "OptiScaler.dll"))

        self.plugin._manual_unpatch_directory_impl(game)
        self.assertEqual((game / "version.dll").read_bytes(), b"CET loader")
        self.assertEqual((game / "winmm.dll").read_bytes(), b"ASI loader")
        self.assertFalse((game / "dxgi.dll").exists())

    def test_old_injector_under_another_proxy_name_is_replaced_not_backed_up(self):
        game = self._game()
        self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
        self._marker(game, dll_name="dxgi.dll")
        old = b"pretend this is the 0.10.0-pre1 injector"
        (game / "winmm.dll").write_bytes(old)
        with mock.patch.object(main, "PREVIOUS_INJECTOR_SHA256S", {hashlib_sha256(old)}):
            result = self.plugin._manual_patch_directory_impl(game, "winmm.dll", VALVE, allow_managed_support_cleanup=True)
        self.assertEqual(result["status"], "success", result)
        self.assertFalse((game / "winmm.dll.b").exists())
        self.assertEqual(sha256(game / "winmm.dll"), main.OPTISCALER_V10_INJECTOR["sha256"])

    def test_never_patched_folder_with_nukem_files_still_backs_up_identical_game_dll(self):
        """dlssg_to_fsr3_amd_is_better.dll from a manual Nukem install is not proof we
        patched the folder: a game DLL identical to the bundle's copy must be backed up."""
        game = self._game(**{"dlssg_to_fsr3_amd_is_better.dll": b"manual nukem install"})
        shutil.copy2(self.fgmod / "amd_fidelityfx_dx12.dll", game / "amd_fidelityfx_dx12.dll")
        result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
        self.assertEqual(result["status"], "success", result)
        self.assertTrue((game / "amd_fidelityfx_dx12.dll.b").exists())
        self.plugin._manual_unpatch_directory_impl(game)
        self.assertTrue((game / "amd_fidelityfx_dx12.dll").exists())

    def test_advanced_unpatch_keeps_marker_and_original_launch_options(self):
        game = self._game()
        self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
        self.plugin._write_marker(
            game / main.MARKER_FILENAME, appid="1", game_name="Fake", dll_name="dxgi.dll", target_dir=game,
            original_launch_options="MY_OPT=1 %command%", backed_up_files=[], fsr4_variant=VALVE,
        )
        result = asyncio.run(self.plugin.manual_unpatch_directory(str(game)))
        self.assertEqual(result["status"], "success", result)
        marker = json.loads((game / main.MARKER_FILENAME).read_text())
        self.assertEqual(marker["original_launch_options"], "MY_OPT=1 %command%")
        self.assertFalse((game / "dxgi.dll").exists())

    def test_marker_target_dir_prefers_marker_parent_over_a_different_stored_path(self):
        live = self._game()
        other = self._game()
        marker = live / main.MARKER_FILENAME
        marker.write_text("{}")
        self.assertEqual(self.plugin._marker_target_dir(marker, {"target_dir": str(other)}), live)
        self.assertEqual(self.plugin._marker_target_dir(marker, {"target_dir": str(TEMP_HOME / "gone")}), live)
        alias = TEMP_HOME / "alias-to-live"
        alias.symlink_to(live)
        self.assertEqual(self.plugin._marker_target_dir(marker, {"target_dir": str(alias)}), alias, "an alias keeps its spelling")

    def test_game_status_flags_an_old_injector(self):
        game = self._game()
        self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
        self.plugin._write_marker(
            game / main.MARKER_FILENAME, appid="7", game_name="Fake", dll_name="dxgi.dll", target_dir=game,
            original_launch_options="", backed_up_files=[], fsr4_variant=VALVE,
        )
        record = {"appid": "7", "name": "Fake", "library_path": str(TEMP_HOME), "install_path": str(game)}
        with mock.patch.object(self.plugin, "_game_record", return_value=record):
            status = asyncio.run(self.plugin.get_game_status("7"))
            self.assertTrue(status["patched"])
            self.assertFalse(status["injector_outdated"])
            (game / "dxgi.dll").write_bytes(b"OLD PRE1 INJECTOR")
            status = asyncio.run(self.plugin.get_game_status("7"))
            self.assertTrue(status["patched"])
            self.assertTrue(status["injector_outdated"])
            self.assertIn("press Reinstall", status["message"])

    def test_valve_094_variant_uses_094_injector_with_valve_dlls(self):
        v094 = "rdna2-valve-411-094"
        game = self._game()
        result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", v094)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(sha256(game / "dxgi.dll"), sha256(self.fgmod / "OptiScaler.dll"), "must be the 0.9.4 injector")
        self.assertEqual(sha256(game / "amdxcffx64.dll"), main.FSR4_VALVE_411_ASSET["sha256"])
        self.assertEqual(sha256(game / "amdxc64.dll"), main.AMDXC64_RDNA2_ASSET["sha256"])
        ini = game / "OptiScaler.ini"
        self.assertEqual(ini_value(ini, "FSR", "Fsr4ForceEnableInt8"), "true")
        self.assertEqual(ini_value(ini, "FSR", "Fsr4Update"), "true")
        self.assertIn(ini_value(ini, "FSR", "Fsr4ForceModel"), (None, "auto"), "v10-only key must not be forced")
        upscaler_sha = sha256(game / "amd_fidelityfx_upscaler_dx12.dll")
        self.assertEqual(self.plugin._detect_fsr4_variant(game, upscaler_sha, game / "dxgi.dll"), v094)

        # The v10 variant shares every DLL except the injector: detection must tell them apart.
        game2 = self._game()
        self.plugin._manual_patch_directory_impl(game2, "dxgi.dll", VALVE)
        self.assertEqual(self.plugin._detect_fsr4_variant(game2, upscaler_sha, game2 / "dxgi.dll"), VALVE)

        # Leaving the 0.9.4 Valve variant resets its override.
        self._marker(game, variant=v094)
        self.plugin._manual_patch_directory_impl(game, "dxgi.dll", "rdna23-int8", allow_managed_support_cleanup=True)
        self.assertEqual(ini_value(ini, "FSR", "Fsr4ForceEnableInt8"), "auto")
        self.assertFalse((game / "amdxc64.dll").exists())

    # ── v0.19 Tier 1 ───────────────────────────────────────────────────────

    def test_default_runtime_is_the_working_deck_variant(self):
        self.assertEqual(main.DEFAULT_FSR4_VARIANT, "rdna2-valve-411-094")
        constants = (PLUGIN_DIR / "src" / "utils" / "constants.ts").read_text(encoding="utf-8")
        self.assertIn('DEFAULT_FSR4_VARIANT: Fsr4VariantValue = "rdna2-valve-411-094"', constants)
        self.assertEqual(self.plugin._normalize_fsr4_variant("bogus"), "rdna2-valve-411-094")

    def test_dx12_upscaler_preset_respects_overlay_choices(self):
        v094 = "rdna2-valve-411-094"
        game = self._game()
        self.plugin._manual_patch_directory_impl(game, "dxgi.dll", v094)
        ini = game / "OptiScaler.ini"
        self.assertEqual(ini_value(ini, "Upscalers", "Dx12Upscaler"), "fsr31")

        # The user picked XeSS in the overlay: a Reinstall must keep it.
        ini.write_text(ini.read_text(encoding="utf-8").replace("Dx12Upscaler=fsr31", "Dx12Upscaler=xess"), encoding="utf-8")
        self._marker(game, variant=v094)
        self.plugin._manual_patch_directory_impl(game, "dxgi.dll", v094, allow_managed_support_cleanup=True)
        self.assertEqual(ini_value(ini, "Upscalers", "Dx12Upscaler"), "xess")
        # ... and leaving the runtime does not touch a value the plugin did not write.
        self.plugin._manual_patch_directory_impl(game, "dxgi.dll", "rdna23-int8", allow_managed_support_cleanup=True)
        self.assertEqual(ini_value(ini, "Upscalers", "Dx12Upscaler"), "xess")

        # Untouched preset goes back to auto when the game leaves the runtime.
        game2 = self._game()
        self.plugin._manual_patch_directory_impl(game2, "dxgi.dll", v094)
        self._marker(game2, variant=v094)
        self.plugin._manual_patch_directory_impl(game2, "dxgi.dll", "rdna23-int8", allow_managed_support_cleanup=True)
        self.assertEqual(ini_value(game2 / "OptiScaler.ini", "Upscalers", "Dx12Upscaler"), "auto")

        # v10 variant uses its own spelling and a switch between the two Valve variants maps it.
        game3 = self._game()
        self.plugin._manual_patch_directory_impl(game3, "dxgi.dll", VALVE)
        self.assertEqual(ini_value(game3 / "OptiScaler.ini", "Upscalers", "Dx12Upscaler"), "ffx")
        self._marker(game3, variant=VALVE)
        self.plugin._manual_patch_directory_impl(game3, "dxgi.dll", v094, allow_managed_support_cleanup=True)
        self.assertEqual(ini_value(game3 / "OptiScaler.ini", "Upscalers", "Dx12Upscaler"), "fsr31")

    def test_watermark_preference_is_applied_on_patch(self):
        game = self._game()
        try:
            self.assertEqual(asyncio.run(self.plugin.set_fsr4_watermark(True))["status"], "success")
            self.assertTrue(asyncio.run(self.plugin.check_fgmod_path())["fsr4_watermark"])
            self.plugin._manual_patch_directory_impl(game, "dxgi.dll", "rdna2-valve-411-094")
            ini = game / "OptiScaler.ini"
            self.assertEqual(ini_value(ini, "FSR", "Fsr4EnableWatermark"), "true")

            asyncio.run(self.plugin.set_fsr4_watermark(False))
            self._marker(game, variant="rdna2-valve-411-094")
            self.plugin._manual_patch_directory_impl(game, "dxgi.dll", "rdna2-valve-411-094", allow_managed_support_cleanup=True)
            self.assertEqual(ini_value(ini, "FSR", "Fsr4EnableWatermark"), "auto")
        finally:
            asyncio.run(self.plugin.set_fsr4_watermark(False))

    def test_game_status_uses_the_marker_file_cache(self):
        game = self._game()
        result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
        self.plugin._write_marker(
            game / main.MARKER_FILENAME, appid="9", game_name="Fake", dll_name="dxgi.dll", target_dir=game,
            original_launch_options="", backed_up_files=[], fsr4_variant=VALVE,
            fsr4_upscaler_sha256=result["fsr4_upscaler_sha256"], file_hashes=result["managed_file_hashes"],
        )
        marker = json.loads((game / main.MARKER_FILENAME).read_text())
        self.assertEqual(set(marker["file_cache"]), {"dxgi.dll", "amd_fidelityfx_upscaler_dx12.dll", "amdxcffx64.dll", "amdxc64.dll"})
        record = {"appid": "9", "name": "Fake", "library_path": str(TEMP_HOME), "install_path": str(game)}
        with mock.patch.object(self.plugin, "_game_record", return_value=record), \
             mock.patch.object(self.plugin, "_file_sha256", wraps=self.plugin._file_sha256) as hasher:
            status = asyncio.run(self.plugin.get_game_status("9"))
            self.assertTrue(status["patched"])
            self.assertEqual(status["fsr4_variant"], VALVE)
            self.assertFalse(status["injector_outdated"])
            self.assertEqual(hasher.call_count, 0, "unchanged files must be served from the cache")
            (game / "dxgi.dll").write_bytes(b"OLD INJECTOR")
            status = asyncio.run(self.plugin.get_game_status("9"))
            self.assertTrue(status["injector_outdated"], "a changed file must be re-hashed")
            self.assertGreater(hasher.call_count, 0)

    def test_setup_skips_re_extraction_when_bundle_is_current(self):
        injector = self.fgmod / "OptiScaler.dll"
        before = injector.stat().st_ino
        result = asyncio.run(self.plugin.run_install_fgmod("rdna23-int8"))
        self.assertEqual(result["status"], "success", result)
        self.assertIn("verified", result["output"])
        self.assertEqual(injector.stat().st_ino, before, "a current bundle must not be re-extracted")
        self.assertEqual(asyncio.run(self.plugin.check_fgmod_path())["selected_fsr4_variant"], "rdna23-int8")

        manifest_path = self.plugin._install_manifest_path(self.fgmod)
        manifest = json.loads(manifest_path.read_text())
        manifest["bundle_fingerprint"] = "stale"
        manifest_path.write_text(json.dumps(manifest))
        result = asyncio.run(self.plugin.run_install_fgmod(VALVE))
        self.assertEqual(result["status"], "success", result)
        self.assertNotIn("verified", result["output"])
        self.assertNotEqual(injector.stat().st_ino, before, "a stale bundle must be rebuilt")
        self.assertEqual(json.loads(manifest_path.read_text())["bundle_fingerprint"], main.BUNDLE_FINGERPRINT)

    # ── v0.20 Tier 2: per-game options + diagnostics ───────────────────────

    def test_per_game_upscaler_and_frame_generation_options(self):
        v094 = "rdna2-valve-411-094"
        game = self._game()
        ini = game / "OptiScaler.ini"
        opts = {"dx12_upscaler": "xess", "frame_generation": "optifg"}
        result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", v094, game_options=opts)
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["game_options"], opts)
        self.assertEqual(ini_value(ini, "Upscalers", "Dx12Upscaler"), "xess")
        self.assertEqual(ini_value(ini, "FrameGen", "Enabled"), "true")
        self.assertEqual(ini_value(ini, "FrameGen", "FGInput"), "upscaler")
        self.assertEqual(ini_value(ini, "FrameGen", "FGOutput"), "fsrfg")

        # Back to auto/default: the plugin's own values are undone and the runtime
        # preset (FSR 3.1 -> 4) applies again.
        self.plugin._write_marker(
            game / main.MARKER_FILENAME, appid="1", game_name="Fake", dll_name="dxgi.dll", target_dir=game,
            original_launch_options="", backed_up_files=[], fsr4_variant=v094, game_options=opts,
        )
        result = self.plugin._manual_patch_directory_impl(
            game, "dxgi.dll", v094, allow_managed_support_cleanup=True,
            game_options={"dx12_upscaler": "auto", "frame_generation": "default"},
        )
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(ini_value(ini, "Upscalers", "Dx12Upscaler"), "fsr31")
        self.assertEqual(ini_value(ini, "FrameGen", "Enabled"), "auto")
        self.assertEqual(ini_value(ini, "FrameGen", "FGInput"), "nukems")
        self.assertEqual(ini_value(ini, "FrameGen", "FGOutput"), "nukems")

        # "fsr4" spells differently per injector; unknown values normalise to auto/default.
        game2 = self._game()
        self.plugin._manual_patch_directory_impl(game2, "dxgi.dll", VALVE, game_options={"dx12_upscaler": "fsr4"})
        self.assertEqual(ini_value(game2 / "OptiScaler.ini", "Upscalers", "Dx12Upscaler"), "ffx")
        self.assertEqual(main._normalize_game_options({"dx12_upscaler": "nope", "frame_generation": 3}),
                         {"dx12_upscaler": "auto", "frame_generation": "default"})

    def test_game_status_reports_options_and_diagnostics_collects_a_report(self):
        game = self._game()
        opts = {"dx12_upscaler": "fsr4", "frame_generation": "default"}
        result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", "rdna2-valve-411-094", game_options=opts)
        self.plugin._write_marker(
            game / main.MARKER_FILENAME, appid="5", game_name="Fake", dll_name="dxgi.dll", target_dir=game,
            original_launch_options="", backed_up_files=[], fsr4_variant="rdna2-valve-411-094",
            fsr4_upscaler_sha256=result["fsr4_upscaler_sha256"], file_hashes=result["managed_file_hashes"], game_options=opts,
        )
        (game / "OptiScaler.log").write_text(
            "12:00:00 OptiScaler v0.9.4 (abc) loaded\nboring line\nSetting DllPath to " + str(game) +
            "\nAmdExtFfxApi::UpdateFfxApiProvider amdxcffx64 loaded from game folder\nlast line\n", encoding="utf-8"
        )
        record = {"appid": "5", "name": "Fake", "library_path": str(TEMP_HOME), "install_path": str(game)}
        with mock.patch.object(self.plugin, "_game_record", return_value=record):
            status = asyncio.run(self.plugin.get_game_status("5"))
            self.assertEqual(status["game_options"], opts)
            self.assertEqual(status["ini_dx12_upscaler"], "fsr31")
            self.assertEqual(status["ini_fg_input"], "nukems")
            diag = asyncio.run(self.plugin.get_game_diagnostics("5"))
        self.assertEqual(diag["status"], "success", diag)
        report = diag["report"]
        for needle in ["Decky Framegen", "variant=rdna2-valve-411-094", "Dx12Upscaler=fsr31", "Fsr4ForceEnableInt8=true",
                       "amdxcffx64 loaded from game folder", "Setting DllPath", "OptiScaler.log: 5 lines", "last line"]:
            self.assertIn(needle, report)
        self.assertNotIn("boring line", report.split("--- last 15 lines ---")[0])
        self.assertTrue(Path(diag["path"]).exists())

    # ── stale bundle detection ─────────────────────────────────────────────

    def test_stale_bundle_is_flagged_and_patch_is_refused(self):
        manifest_path = self.plugin._install_manifest_path(self.fgmod)
        manifest = json.loads(manifest_path.read_text())
        good = json.dumps(manifest)
        injector_dir = self.fgmod / main.FSR4_VARIANTS[VALVE]["dir_name"]
        injector = injector_dir / "OptiScaler.dll"
        good_bytes = injector.read_bytes()
        try:
            # Simulate a ~/fgmod prepared by v0.17 (old pre1 injector recorded and on disk).
            manifest["fsr4_variants"][VALVE]["injector"]["sha256"] = "b374b19081cc066365d0c6da4808d768e16469b0cbdfc478b6e95999947d5364"
            manifest_path.write_text(json.dumps(manifest))
            injector.write_bytes(b"OLD PRE1 DLL")

            status = asyncio.run(self.plugin.check_fgmod_path())
            self.assertTrue(status["exists"], "an outdated bundle must not hide the installed UI")
            self.assertTrue(status["bundle_outdated"])
            self.assertEqual(status["outdated_variants"], [VALVE])
            self.assertEqual(status["selected_fsr4_variant"], VALVE)

            game = self._game()
            result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", VALVE)
            self.assertEqual(result["status"], "error")
            self.assertIn("older plugin build", result["message"])
            self.assertIn("Update OptiScaler bundle", result["message"], "must name the button the UI shows in this state")
            self.assertEqual(sorted(p.name for p in game.iterdir()), ["Game.exe"], "a refused patch must not touch the game")

            # Other runtimes do not depend on that injector and keep working.
            result = self.plugin._manual_patch_directory_impl(game, "dxgi.dll", "rdna23-int8")
            self.assertEqual(result["status"], "success", result)
        finally:
            manifest_path.write_text(good)
            injector.write_bytes(good_bytes)

        status = asyncio.run(self.plugin.check_fgmod_path())
        self.assertFalse(status["bundle_outdated"])
        self.assertEqual(status["outdated_variants"], [])

    # ── launch options ─────────────────────────────────────────────────────

    def test_is_managed_launch_options_table(self):
        managed = self.plugin._is_managed_launch_options
        self.assertTrue(managed("WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%"))
        self.assertTrue(managed('WINEDLLOVERRIDES="winmm=n,b" SteamDeck=0 %command%'))
        self.assertTrue(managed("  WINEDLLOVERRIDES=version=n,b   SteamDeck=0   %command% "))
        self.assertTrue(managed("~/fgmod/fgmod %command%"))
        self.assertTrue(managed("DLL=winmm.dll ~/fgmod/fgmod %command%"))
        self.assertFalse(managed("SteamDeck=0 %command%"), "a user could have typed this themselves")
        self.assertTrue(managed("SteamDeck=0 %command%", managed_dll_name="OptiScaler.asi"))
        self.assertFalse(managed('WINEDLLOVERRIDES="dxgi=n,b" %command%'), "ReShade-style override without our SteamDeck=0")
        self.assertFalse(managed("gamemoderun %command%"))
        self.assertFalse(managed(""))

    # ── runtime plumbing ───────────────────────────────────────────────────

    def test_files_match_semantics_and_no_filecmp_import(self):
        a = TEMP_HOME / "a.bin"
        b = TEMP_HOME / "b.bin"
        c = TEMP_HOME / "c.bin"
        a.write_bytes(b"x" * 3000)
        b.write_bytes(b"x" * 3000)
        c.write_bytes(b"x" * 2999 + b"y")
        self.assertTrue(self.plugin._files_match(a, b))
        self.assertFalse(self.plugin._files_match(a, c))
        self.assertFalse(self.plugin._files_match(a, TEMP_HOME / "missing.bin"))
        self.assertFalse(self.plugin._files_match(a, TEMP_HOME))

        tree = ast.parse((PLUGIN_DIR / "main.py").read_text(encoding="utf-8"))
        imported = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        # Modules Decky Loader's PyInstaller bundle is known to contain, plus decky.
        allowed = {"decky", "os", "subprocess", "json", "shutil", "re", "hashlib", "datetime", "pathlib"}
        self.assertTrue(imported <= allowed, f"unexpected top-level imports: {imported - allowed}")

    def test_ps_runs_with_clean_ld_library_path_and_tolerates_failure(self):
        exe = TEMP_HOME / "SomeGame" / "Game.exe"
        exe.parent.mkdir(exist_ok=True)
        exe.write_bytes(b"MZ")
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return subprocess.CompletedProcess(cmd, 0, stdout=f"wine64 Z:{exe}\n", stderr="")

        with mock.patch.object(main.subprocess, "run", side_effect=fake_run), \
             mock.patch.dict(main.os.environ, {"LD_LIBRARY_PATH": "/tmp/_MEIxyz"}):
            self.assertEqual(self.plugin._best_running_executable([exe]), exe)
        self.assertEqual(calls[0][0][:2], ["ps", "-eo"])
        self.assertEqual(calls[0][1]["env"]["LD_LIBRARY_PATH"], "")

        def failing_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="ps: boom")

        with mock.patch.object(main.subprocess, "run", side_effect=failing_run):
            self.assertIsNone(self.plugin._best_running_executable([exe]))

    def test_running_exe_matches_symlinked_library_spelling(self):
        real = TEMP_HOME / "real-library" / "steamapps" / "common" / "G"
        real.mkdir(parents=True)
        (real / "G.exe").write_bytes(b"MZ")
        link = TEMP_HOME / "link-library"
        link.symlink_to(TEMP_HOME / "real-library")
        exe_via_link = link / "steamapps" / "common" / "G" / "G.exe"

        def fake_run(cmd, **kwargs):
            # Steam launches through the real path even when the library was found via a symlink.
            return subprocess.CompletedProcess(cmd, 0, stdout=f"wine64 {(real / 'G.exe').resolve()}\n", stderr="")

        with mock.patch.object(main.subprocess, "run", side_effect=fake_run):
            self.assertEqual(self.plugin._best_running_executable([exe_via_link]), exe_via_link)


if __name__ == "__main__":
    unittest.main()

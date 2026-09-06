"""App-ID based patch/unpatch/status against a simulated Steam library.

Builds ~/.local/share/Steam with libraryfolders.vdf pointing at a second
library (like an SD card), appmanifest files, and an Unreal-style install
tree, then drives the same backend methods the Decky UI calls.

    python3 -m unittest tests/test_steam_library.py -v
"""

from __future__ import annotations

import asyncio
import json
import shutil
import unittest
from pathlib import Path

from _harness import TEMP_HOME, main, reset_home, sha256

VALVE = "rdna2-valve-411-pre10"


def write_manifest(steamapps: Path, appid: str, name: str, installdir: str) -> None:
    (steamapps / f"appmanifest_{appid}.acf").write_text(
        '"AppState"\n{\n'
        f'\t"appid"\t\t"{appid}"\n'
        f'\t"name"\t\t"{name}"\n'
        f'\t"installdir"\t\t"{installdir}"\n'
        "}\n",
        encoding="utf-8",
    )


class SteamLibraryTests(unittest.TestCase):
    plugin: main.Plugin

    @classmethod
    def setUpClass(cls) -> None:
        reset_home()
        cls.plugin = main.Plugin()
        result = asyncio.run(cls.plugin.extract_static_optiscaler("rdna23-int8"))
        assert result["status"] == "success", result

        cls.steam_root = TEMP_HOME / ".local" / "share" / "Steam"
        cls.sd_library = TEMP_HOME / "sdcard" / "steamapps folder (1)"  # spaces + parentheses on purpose
        main_apps = cls.steam_root / "steamapps"
        sd_apps = cls.sd_library / "steamapps"
        main_apps.mkdir(parents=True)
        sd_apps.mkdir(parents=True)
        (main_apps / "libraryfolders.vdf").write_text(
            '"libraryfolders"\n{\n'
            '\t"0"\n\t{\n\t\t"path"\t\t"' + str(cls.steam_root) + '"\n\t}\n'
            '\t"1"\n\t{\n\t\t"path"\t\t"' + str(cls.sd_library) + '"\n\t}\n'
            "}\n",
            encoding="utf-8",
        )

        # Unreal-style game in the main library: launcher exe at root must lose to the shipping exe.
        ue_root = main_apps / "common" / "Fake UE Game"
        ue_bin = ue_root / "FakeGame" / "Binaries" / "Win64"
        ue_bin.mkdir(parents=True)
        (ue_root / "Engine" / "Binaries" / "Win64").mkdir(parents=True)
        (ue_root / "Engine" / "Binaries" / "Win64" / "CrashReportClient.exe").write_bytes(b"MZ")
        (ue_root / "FakeGame.exe").write_bytes(b"MZ")  # bootstrap launcher
        (ue_bin / "FakeGame-Win64-Shipping.exe").write_bytes(b"MZ")
        write_manifest(main_apps, "111", "Fake UE Game", "Fake UE Game")
        cls.ue_bin = ue_bin

        # Flat game on the "SD card" library that already ships its own libxess.dll and dxgi.dll.
        sd_root = sd_apps / "common" / "Flat Game"
        sd_root.mkdir(parents=True)
        (sd_root / "FlatGame.exe").write_bytes(b"MZ")
        (sd_root / "libxess.dll").write_bytes(b"game's own libxess")
        (sd_root / "dxgi.dll").write_bytes(b"reshade dxgi")
        write_manifest(sd_apps, "222", "Flat Game", "Flat Game")
        cls.sd_root = sd_root

        write_manifest(main_apps, "333", "Proton 9.0 (Beta)", "Proton 9.0")
        write_manifest(main_apps, "444", "Missing Game", "Not Installed Dir")

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEMP_HOME, ignore_errors=True)

    def test_library_discovery_skips_proton_and_dedupes(self):
        result = asyncio.run(self.plugin.list_installed_games())
        self.assertEqual(result["status"], "success", result)
        by_id = {g["appid"]: g for g in result["games"]}
        self.assertEqual(set(by_id), {"111", "222", "444"})
        self.assertTrue(by_id["111"]["install_found"])
        self.assertTrue(by_id["222"]["install_found"], "SD-card library with spaces/parentheses must be found")
        self.assertFalse(by_id["444"]["install_found"])

    def test_ue_game_targets_shipping_exe_folder(self):
        result = asyncio.run(self.plugin.patch_game("111", "dxgi.dll", "", VALVE))
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(Path(result["target_dir"]), self.ue_bin)
        self.assertEqual(result["launch_options"], "WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%")
        self.assertEqual(sha256(self.ue_bin / "dxgi.dll"), main.OPTISCALER_V10_INJECTOR["sha256"])
        marker = json.loads((self.ue_bin / main.MARKER_FILENAME).read_text())
        self.assertEqual(marker["fsr4_variant"], VALVE)

        status = asyncio.run(self.plugin.get_game_status("111"))
        self.assertTrue(status["patched"], status)
        self.assertEqual(status["fsr4_variant"], VALVE)
        self.assertEqual(status["dll_name"], "dxgi.dll")

        result = asyncio.run(self.plugin.unpatch_game("111"))
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["launch_options"], "")
        self.assertFalse((self.ue_bin / "dxgi.dll").exists())
        self.assertFalse((self.ue_bin / main.MARKER_FILENAME).exists())
        self.assertFalse(asyncio.run(self.plugin.get_game_status("111"))["patched"])

    def test_flat_game_keeps_user_launch_options_and_restores_originals(self):
        user_opts = "PROTON_LOG=1 %command%"
        result = asyncio.run(self.plugin.patch_game("222", "winmm.dll", user_opts, "rdna4-native"))
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["original_launch_options"], user_opts)
        self.assertEqual(result["launch_options"], "WINEDLLOVERRIDES=winmm=n,b SteamDeck=0 %command%")
        # Reshade's dxgi.dll is not our proxy name but is a known proxy: backed up, not clobbered.
        self.assertEqual((self.sd_root / "dxgi.dll.b").read_bytes(), b"reshade dxgi")
        self.assertEqual(sha256(self.sd_root / "winmm.dll"), sha256(TEMP_HOME / "fgmod" / "OptiScaler.dll"))

        # Re-patch with a managed launch string must keep the true original options.
        result = asyncio.run(self.plugin.patch_game("222", "winmm.dll", result["launch_options"], "rdna4-native"))
        self.assertEqual(result["original_launch_options"], user_opts)

        result = asyncio.run(self.plugin.unpatch_game("222"))
        self.assertEqual(result["status"], "success", result)
        self.assertEqual(result["launch_options"], user_opts)
        self.assertEqual((self.sd_root / "dxgi.dll").read_bytes(), b"reshade dxgi")
        self.assertFalse((self.sd_root / "winmm.dll").exists())

    def test_missing_install_dir_is_reported_not_crashed(self):
        status = asyncio.run(self.plugin.get_game_status("444"))
        self.assertEqual(status["status"], "success")
        self.assertFalse(status["install_found"])
        result = asyncio.run(self.plugin.patch_game("444", "dxgi.dll", "", VALVE))
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()

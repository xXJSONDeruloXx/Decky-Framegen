import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "py_modules"))

from services import config
from services.bundle import BundleManager
from services.patcher import PatchManager
from services.steam import SteamLibrary


class BackendSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.home = root / "home"
        self.plugin_dir = root / "plugin"
        self.home.mkdir()
        self.plugin_dir.mkdir()

        bundle_path = self.home / "fgmod"
        (bundle_path / "renames").mkdir(parents=True)
        (bundle_path / "plugins").mkdir()
        (bundle_path / "fsr4-rdna2-3").mkdir()
        (bundle_path / "OptiScaler.dll").write_bytes(b"optiscaler")
        (bundle_path / "renames" / "dxgi.dll").write_bytes(b"managed-proxy")
        (bundle_path / "OptiScaler.ini").write_text("FGInput=auto\nFGOutput=auto\n", encoding="utf-8")
        (bundle_path / "plugins" / "OptiPatcher.asi").write_bytes(b"plugin")
        (bundle_path / "fsr4-rdna2-3" / "amd_fidelityfx_upscaler_dx12.dll").write_bytes(b"upscaler")

        logger = lambda _message: None
        bundle = BundleManager(self.home, self.plugin_dir, logger)
        self.manager = PatchManager(self.home, bundle, SteamLibrary(self.home, logger), logger)
        self.target = root / "game"
        (self.target / "plugins").mkdir(parents=True)
        (self.target / "plugins" / "keep.txt").write_text("user-owned", encoding="utf-8")
        (self.target / "dxgi.dll").write_bytes(b"original-game-proxy")
        (self.target / "OptiScaler.ini").write_text("FGInput=auto\nFGOutput=auto\nUserSetting=true\n", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_patch_and_unpatch_preserve_unowned_files(self):
        result = self.manager.manual_patch_directory(str(self.target), "dxgi.dll", "rdna23-int8", "auto")
        self.assertEqual(result["status"], "success")
        self.assertTrue((self.target / "FRAMEGEN_PATCH").exists())
        self.assertTrue((self.target / "dxgi.dll.b").exists())
        self.assertTrue((self.target / "plugins" / "keep.txt").exists())

        cleanup = self.manager.manual_unpatch_directory(str(self.target))
        self.assertEqual(cleanup["status"], "success")
        self.assertFalse((self.target / "FRAMEGEN_PATCH").exists())
        self.assertEqual((self.target / "dxgi.dll").read_bytes(), b"original-game-proxy")
        self.assertEqual((self.target / "plugins" / "keep.txt").read_text(encoding="utf-8"), "user-owned")
        self.assertEqual(
            (self.target / "OptiScaler.ini").read_text(encoding="utf-8"),
            "FGInput=auto\nFGOutput=auto\nUserSetting=true\n",
        )
        self.assertFalse((self.target / "plugins" / "OptiPatcher.asi").exists())

    def test_unpatch_refuses_modified_managed_file_and_keeps_marker(self):
        result = self.manager.manual_patch_directory(str(self.target), "dxgi.dll", "rdna23-int8", "nukems")
        self.assertEqual(result["status"], "success")
        (self.target / "dxgi.dll").write_bytes(b"user-modified")

        cleanup = self.manager.manual_unpatch_directory(str(self.target))
        self.assertEqual(cleanup["status"], "error")
        self.assertTrue((self.target / "FRAMEGEN_PATCH").exists())
        self.assertEqual((self.target / "dxgi.dll").read_bytes(), b"user-modified")
        self.assertTrue((self.target / "plugins" / "keep.txt").exists())

    def test_appid_unpatch_propagates_cleanup_failure(self):
        class FakeSteam:
            def game_record(self, appid):
                return {"appid": appid, "name": "Test Game", "install_path": str(self_target)}

            def is_game_running(self, _game_info):
                return False

            def guess_patch_target(self, _game_info):
                return self_target, None

        self_target = self.target
        self.manager.steam = FakeSteam()
        result = self.manager.patch_game("123", "dxgi.dll", "", "rdna23-int8", "auto")
        self.assertEqual(result["status"], "success")
        (self.target / "dxgi.dll").write_bytes(b"modified after patch")

        cleanup = self.manager.unpatch_game("123")
        self.assertEqual(cleanup["status"], "error")
        self.assertTrue((self.target / "FRAMEGEN_PATCH").exists())

    def test_backend_configuration_is_explicit(self):
        ini_file = self.target / "backend.ini"
        ini_file.write_text("FGInput=auto\nFGOutput=auto\n", encoding="utf-8")
        self.assertTrue(config.configure(ini_file, "nukems"))
        self.assertIn("FGInput=nukems", ini_file.read_text(encoding="utf-8"))
        self.assertIn("FGOutput=nukems", ini_file.read_text(encoding="utf-8"))
        self.assertTrue(config.configure(ini_file, "auto"))
        self.assertIn("FGInput=auto", ini_file.read_text(encoding="utf-8"))
        self.assertIn("FGOutput=auto", ini_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

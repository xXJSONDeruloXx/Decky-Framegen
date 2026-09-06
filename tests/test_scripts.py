"""Checks for the shell wrapper scripts and the env-var INI updater.

Runs the real scripts under bash with a fake ~/fgmod (tiny placeholder files),
a stub `logger`/`zenity` on PATH and HOME pointed at a temp dir.

    python3 -m unittest discover -s tests -t tests -v
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent
ASSETS = PLUGIN_DIR / "assets" if (PLUGIN_DIR / "assets" / "fgmod.sh").exists() else PLUGIN_DIR / "defaults" / "assets"
BASH = shutil.which("bash")


def _write_exec(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def parse_winedlloverrides(value: str) -> dict[str, str]:
    """Minimal port of Wine's loadorder parser: entries split on ';', names before
    the first '=' split on ',', order string after '='. Empty entries are skipped."""
    result: dict[str, str] = {}
    for entry in value.split(";"):
        if not entry or "=" not in entry:
            continue
        names, order = entry.split("=", 1)
        for name in names.replace(" ", ",").split(","):
            if name:
                result[name.lower()] = order
    return result


@unittest.skipUnless(BASH, "bash not available")
class WineDllOverridesTests(unittest.TestCase):
    def _join(self, preset: str | None, script: Path, dll_name: str) -> str:
        line = next(l for l in script.read_text().splitlines() if "export WINEDLLOVERRIDES=" in l).strip()
        env = {"PATH": os.environ["PATH"]}
        if preset is not None:
            env["WINEDLLOVERRIDES"] = preset
        code = f'dll_name="{dll_name}"; _wine_dll="${{dll_name%.dll}}"; {line}; printf "%s" "$WINEDLLOVERRIDES"'
        return subprocess.run([BASH, "-c", code], capture_output=True, text=True, env=env, check=True).stdout

    def test_fgmod_join_keeps_existing_overrides_and_ours(self):
        script = ASSETS / "fgmod.sh"
        self.assertEqual(self._join(None, script, "winmm.dll"), "winmm=n,b")
        self.assertEqual(self._join("", script, "winmm.dll"), "winmm=n,b")
        joined = self._join("dinput8=n,b", script, "winmm.dll")
        self.assertEqual(parse_winedlloverrides(joined), {"dinput8": "n,b", "winmm": "n,b"})
        joined = self._join("dinput8=n,b;", script, "dxgi.dll")
        self.assertEqual(parse_winedlloverrides(joined), {"dinput8": "n,b", "dxgi": "n,b"})

    def test_uninstaller_join(self):
        script = ASSETS / "fgmod-uninstaller.sh"
        line = next(l for l in script.read_text().splitlines() if "export WINEDLLOVERRIDES=" in l).strip()
        out = subprocess.run(
            [BASH, "-c", f'{line}; printf "%s" "$WINEDLLOVERRIDES"'],
            capture_output=True, text=True, env={"PATH": os.environ["PATH"], "WINEDLLOVERRIDES": "dinput8=n,b"}, check=True,
        ).stdout
        self.assertEqual(parse_winedlloverrides(out), {"dinput8": "n,b", "dxgi": "n,b"})


@unittest.skipUnless(BASH, "bash not available")
class FgmodWrapperTests(unittest.TestCase):
    """Runs fgmod.sh in stand-alone mode (single argument = exe path) with a fake bundle."""

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="fgmod-script-home-"))
        fgmod = self.home / "fgmod"
        (fgmod / "renames").mkdir(parents=True)
        (fgmod / "plugins").mkdir()
        (fgmod / "fsr4-rdna2-3").mkdir()
        for name in ["OptiScaler.dll", "libxess.dll", "libxess_dx11.dll", "libxess_fg.dll", "libxell.dll",
                     "amd_fidelityfx_dx12.dll", "amd_fidelityfx_framegeneration_dx12.dll", "amd_fidelityfx_vk.dll",
                     "dlssg_to_fsr3_amd_is_better.dll", "fakenvapi.dll", "fakenvapi.ini", "amd_fidelityfx_upscaler_dx12.dll"]:
            (fgmod / name).write_bytes(b"bundle " + name.encode())
        (fgmod / "fsr4-rdna2-3" / "amd_fidelityfx_upscaler_dx12.dll").write_bytes(b"bundle upscaler 402c")
        (fgmod / "renames" / "dxgi.dll").write_bytes(b"bundle OptiScaler.dll")
        (fgmod / "renames" / "winmm.dll").write_bytes(b"bundle OptiScaler.dll")
        (fgmod / "plugins" / "OptiPatcher.asi").write_bytes(b"asi")
        (fgmod / "OptiScaler.ini").write_text("[FrameGen]\nFGInput=nukems\nFGOutput=nukems\n[Menu]\nUseHQFont=auto\n", encoding="utf-8")
        shutil.copy2(ASSETS / "update-optiscaler-config.py", fgmod / "update-optiscaler-config.py")
        (fgmod / "install-manifest.json").write_text('{"selected_default_variant": "rdna23-int8"}')

        self.bin = self.home / "bin"
        self.bin.mkdir()
        _write_exec(self.bin / "logger", "#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> \"$HOME/logger.log\"\n")
        _write_exec(self.bin / "zenity", "#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> \"$HOME/zenity.log\"\nexit 5\n")
        self.env = {**os.environ, "HOME": str(self.home), "PATH": f"{self.bin}:{os.environ['PATH']}", "STEAM_ZENITY": str(self.bin / "zenity")}

    def tearDown(self) -> None:
        shutil.rmtree(self.home, ignore_errors=True)

    def _run(self, *args: str, cwd: Path | None = None, extra_env: dict | None = None) -> subprocess.CompletedProcess:
        env = {**self.env, **(extra_env or {})}
        return subprocess.run([BASH, str(ASSETS / "fgmod.sh"), *args], capture_output=True, text=True, env=env, cwd=cwd or self.home, timeout=120)

    def test_patches_exe_folder_and_honours_dll_env(self):
        game = self.home / "Some Game (Deluxe)"
        game.mkdir()
        (game / "Game.exe").write_bytes(b"MZ")
        (game / "libxess.dll").write_bytes(b"game xess")
        result = self._run(str(game / "Game.exe"), extra_env={"DLL": "winmm.dll"})
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
        self.assertEqual((game / "winmm.dll").read_bytes(), b"bundle OptiScaler.dll")
        self.assertFalse((game / "dxgi.dll").exists())
        self.assertEqual((game / "libxess.dll.b").read_bytes(), b"game xess", "game-shipped XeSS DLL must be backed up")
        self.assertEqual((game / "libxess.dll").read_bytes(), b"bundle libxess.dll")
        self.assertTrue((game / "plugins" / "OptiPatcher.asi").exists())
        self.assertTrue((game / "OptiScaler.ini").exists())

    def test_engine_folder_without_shipping_exe_never_targets_cwd(self):
        root = self.home / "UE Game"
        (root / "Engine" / "Binaries" / "Win64").mkdir(parents=True)
        deep = root / "Content" / "Proj" / "Binaries" / "Win64"  # depth 5: not found by the depth-4 search
        deep.mkdir(parents=True)
        (deep / "Proj-Win64-Shipping.exe").write_bytes(b"MZ")
        (root / "Proj.exe").write_bytes(b"MZ")
        elsewhere = self.home / "unrelated-cwd"
        elsewhere.mkdir()

        result = self._run(str(root / "Proj.exe"), cwd=elsewhere)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
        self.assertEqual(list(elsewhere.iterdir()), [], "the script must never patch the current working directory")
        self.assertTrue((root / "dxgi.dll").exists())
        self.assertIn("keeping", (self.home / "logger.log").read_text())

    def test_foreign_proxy_is_backed_up_on_relaunch_of_a_patched_folder(self):
        game = self.home / "Patched"
        game.mkdir()
        (game / "Game.exe").write_bytes(b"MZ")
        self.assertEqual(self._run(str(game / "Game.exe")).returncode, 0)
        (game / "version.dll").write_bytes(b"foreign mod loader")
        result = self._run(str(game / "Game.exe"))
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
        self.assertEqual((game / "version.dll.b").read_bytes(), b"foreign mod loader")
        self.assertFalse((game / "dxgi.dll.b").exists(), "our own proxy must not be backed up")
        self.assertEqual((game / "dxgi.dll").read_bytes(), b"bundle OptiScaler.dll")

    def test_valve_094_defaults_are_soft_and_watermark_follows_manifest(self):
        fgmod = self.home / "fgmod"
        vdir = fgmod / "fsr4-rdna2-valve-411-094"
        vdir.mkdir()
        for name in ("amd_fidelityfx_upscaler_dx12.dll", "amdxcffx64.dll", "amdxc64.dll"):
            (vdir / name).write_bytes(b"valve " + name.encode())
        (fgmod / "install-manifest.json").write_text('{"selected_default_variant": "rdna2-valve-411-094", "fsr4_watermark": true}')

        auto = self.home / "Auto"
        auto.mkdir()
        (auto / "Game.exe").write_bytes(b"MZ")
        (auto / "OptiScaler.ini").write_text("[Upscalers]\nDx12Upscaler=auto\n[FSR]\nFsr4ForceEnableInt8=auto\nFsr4EnableWatermark=auto\n", encoding="utf-8")
        result = self._run(str(auto / "Game.exe"))
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
        ini = (auto / "OptiScaler.ini").read_text(encoding="utf-8")
        self.assertIn("Dx12Upscaler=fsr31", ini)
        self.assertIn("Fsr4ForceEnableInt8=true", ini)
        self.assertIn("Fsr4EnableWatermark=true", ini)
        self.assertEqual((auto / "amdxc64.dll").read_bytes(), b"valve amdxc64.dll")

        chosen = self.home / "Chosen"
        chosen.mkdir()
        (chosen / "Game.exe").write_bytes(b"MZ")
        (chosen / "OptiScaler.ini").write_text("[Upscalers]\nDx12Upscaler=xess\n", encoding="utf-8")
        self.assertEqual(self._run(str(chosen / "Game.exe")).returncode, 0)
        self.assertIn("Dx12Upscaler=xess", (chosen / "OptiScaler.ini").read_text(encoding="utf-8"))

    def test_error_dialog_has_timeout_and_logs_first(self):
        result = self._run(str(self.home / "does-not-exist" / "Game.exe"))
        self.assertEqual(result.returncode, 1)
        zenity_log = (self.home / "zenity.log").read_text()
        self.assertIn("--timeout=", zenity_log)
        self.assertIn("ERROR:", (self.home / "logger.log").read_text())

    def test_v10_fg_keys_are_mapped_back_for_094_runtimes(self):
        game = self.home / "Flat"
        game.mkdir()
        (game / "Game.exe").write_bytes(b"MZ")
        (game / "OptiScaler.ini").write_text(
            "[FrameGen]\nFGInput=NvngxFG\nFGOutput=NoFG\nFGNvngxReplacement=Nukems\n[Menu]\nUseHQFont=false\n", encoding="utf-8"
        )
        result = self._run(str(game / "Game.exe"))
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
        ini = (game / "OptiScaler.ini").read_text(encoding="utf-8")
        self.assertIn("FGInput=nukems", ini)
        self.assertIn("FGOutput=nukems", ini)
        self.assertIn("FGNvngxReplacement=Nukems", ini)


class UpdateOptiscalerConfigTests(unittest.TestCase):
    def test_backslash_values_are_written_literally(self):
        with tempfile.TemporaryDirectory() as tmp:
            ini = Path(tmp) / "OptiScaler.ini"
            ini.write_text("[Menu]\nTTFFontPath=auto\nFpsShortcutKey=auto\nScale=auto\n", encoding="utf-8")
            env = {**os.environ, "TTFFontPath": r"C:\Windows\Fonts\comic.ttf", "Menu_FpsShortcutKey": "0x21&", "Scale": r"C:\new\1font"}
            result = subprocess.run(["python3", str(ASSETS / "update-optiscaler-config.py"), str(ini)], capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = ini.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines, ["[Menu]", r"TTFFontPath=C:\Windows\Fonts\comic.ttf", "FpsShortcutKey=0x21&", r"Scale=C:\new\1font"])


if __name__ == "__main__":
    unittest.main()

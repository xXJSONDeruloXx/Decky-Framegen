# Only stdlib modules that Decky Loader's PyInstaller bundle already contains are
# imported here (no filecmp: it is resolved from the *system* Python's stdlib,
# which on SteamOS 3.7 is a different major version than the loader's 3.11).
import decky
import os
import subprocess
import json
import shutil
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path

OPTISCALER_ARCHIVE_ASSET = {
    "name": "Optiscaler_0.9.4-final.20260718._MM.7z",
    "sha256": "575cb4df866116093df75af607e37fd70e10f5163e0f23fd5c804142e80ef0ad",
    "version": "0.9.4-final.20260718",
}

FSR4_INT8_ASSET = {
    "name": "amd_fidelityfx_upscaler_dx12.dll",
    "sha256": "c7720bc16bede334f59a1a32cd22edbcbbb159685ed5240e61350a5fb0bc8a94",
    "version": "4.0.2c",
}

FSR4_OFFICIAL_411_ASSET = {
    "name": "amdxcffx64.dll",
    "sha256": "a2b136b6affd35a49b141a936be935f7d5ddc8d8f9b8c9afbe62ff9ddb2538a0",
    "version": "4.1.1-official",
}

FSR4_VALVE_411_ASSET = {
    "name": "amdxcffx64_valve_2.3.0.2913.dll",
    "sha256": "4e7dc37aebea3a90e3d3cc43e24cb2b54176b2535315f20dbe63b3b7cfc56b1e",
    "version": "4.1.1-valve-2.3.0.2913",
}

AMDXC64_RDNA2_ASSET = {
    "name": "amdxc64.dll",
    "sha256": "a0a0af61d475e30a70966b3459f3793df772faf8f26ae3261d10554ff592cbd5",
    "version": "8.18.10.0474",
}

# Official OptiScaler v10 nightly (optiscaler/OptiScaler-nightly). Only its root
# OptiScaler.dll is used, as the injector for the Valve RDNA2 FSR 4.1.1 runtime.
#
# Why a nightly and not the old 0.10.0-pre1 (22 Jun 2026, 54d99b43) DLL: that build
# shipped a brand-new menu input system that predates upstream's Linux/Proton fixes
# (27 Jun "Prevent stucking at startup on Linux", 2-4 Sep input-system fixes). Under
# Proton the overlay opened but never received input: greyed out, unclickable, and
# Insert could not close it. The nightly carries those fixes plus the same
# LoadCustomAmdxc64OnRdna2 / Fsr4ForceModel support the RDNA2 path relies on.
OPTISCALER_V10_ARCHIVE_ASSET = {
    "name": "OptiScaler_v10.0.0-pre1_20260905.7z",
    "sha256": "bc87598d8622ec938089582e88f1689d708a7db76c68dfe415e514c5b13216ed",
    "version": "v10.0.0-dev.20260905 (da70e61e)",
}

OPTISCALER_V10_INJECTOR = {
    "name": "OptiScaler.dll",
    "sha256": "c5f06953d91f01593b1e44273dccb76326aa3725f92eb32e7aebe114383e927e",
}

# Injectors shipped by earlier plugin builds. A proxy DLL with one of these hashes
# is ours even though no file in the current ~/fgmod matches it byte-for-byte, so
# it must be replaced, never backed up as a "game original".
PREVIOUS_INJECTOR_SHA256S = {
    "b374b19081cc066365d0c6da4808d768e16469b0cbdfc478b6e95999947d5364",  # 0.10.0-pre1 20260622 (v0.16-v0.17 Valve RDNA2)
}

OPTIPATCHER_ASSET = {
    "name": "OptiPatcher_rolling.asi",
    "sha256": "88b9e1be3559737cd205fdf5f2c8550cf1923fb1def4c603e5bf03c3e84131b1",
    "version": "rolling",
}

FSR4_UPSCALER_FILENAME = "amd_fidelityfx_upscaler_dx12.dll"
FSR4_DRIVER_OVERRIDE_FILENAME = "amdxcffx64.dll"
INSTALL_MANIFEST_FILENAME = "install-manifest.json"
VERSION_FILENAME = "version.txt"
# Steam Deck default: the Valve RDNA2 driver DLLs with the 0.9.4 injector (the v10
# injector's overlay ignores the mouse under gamescope). Existing installs keep
# whatever their manifest records.
DEFAULT_FSR4_VARIANT = "rdna2-valve-411-094"

# Bumped whenever the prepared ~/fgmod layout or its INI modifications change, so
# a Setup on an existing bundle knows whether a full re-extraction is needed.
BUNDLE_LAYOUT_VERSION = 2

FSR4_VARIANTS = {
    "rdna23-int8": {
        "label": "4.0.2c / RDNA2-3 compatibility",
        "dir_name": "fsr4-rdna2-3",
        "sha256": "c7720bc16bede334f59a1a32cd22edbcbbb159685ed5240e61350a5fb0bc8a94",
        "source_asset_name": FSR4_INT8_ASSET["name"],
        "source_version": FSR4_INT8_ASSET["version"],
        "uses_archive_native": False,
        "extra_files": [],
    },
    "rdna4-native": {
        "label": "4.1.1 SDK / RDNA3 dGPU + RDNA4",
        "dir_name": "fsr4-rdna4",
        "sha256": "d0dcccc74a43c44ba435b7a369b456e0970d8a4464e4bd683119b374f2c9fb46",
        "source_asset_name": OPTISCALER_ARCHIVE_ASSET["name"],
        "source_version": OPTISCALER_ARCHIVE_ASSET["version"],
        "uses_archive_native": True,
        "extra_files": [],
    },
    "rdna34-official-411": {
        "label": "4.1.1 driver override / RDNA3-4",
        "dir_name": "fsr4-rdna3-4-official-411",
        "sha256": "d0dcccc74a43c44ba435b7a369b456e0970d8a4464e4bd683119b374f2c9fb46",
        "source_asset_name": OPTISCALER_ARCHIVE_ASSET["name"],
        "source_version": OPTISCALER_ARCHIVE_ASSET["version"],
        "uses_archive_native": True,
        "extra_files": [
            {
                "name": FSR4_DRIVER_OVERRIDE_FILENAME,
                "sha256": FSR4_OFFICIAL_411_ASSET["sha256"],
                "source_asset_name": FSR4_OFFICIAL_411_ASSET["name"],
                "source_version": FSR4_OFFICIAL_411_ASSET["version"],
            }
        ],
        "config_overrides": {},
    },
    "rdna2-valve-411-pre10": {
        "label": "4.1.1 Valve RDNA2 compatibility",
        "dir_name": "fsr4-rdna2-valve-411-pre10",
        "sha256": "d0dcccc74a43c44ba435b7a369b456e0970d8a4464e4bd683119b374f2c9fb46",
        "source_asset_name": OPTISCALER_ARCHIVE_ASSET["name"],
        "source_version": OPTISCALER_ARCHIVE_ASSET["version"],
        "uses_archive_native": True,
        "injector": {
            "name": OPTISCALER_V10_INJECTOR["name"],
            "sha256": OPTISCALER_V10_INJECTOR["sha256"],
            "source_asset_name": OPTISCALER_V10_ARCHIVE_ASSET["name"],
            "source_version": OPTISCALER_V10_ARCHIVE_ASSET["version"],
        },
        "extra_files": [
            {
                "name": FSR4_DRIVER_OVERRIDE_FILENAME,
                "sha256": FSR4_VALVE_411_ASSET["sha256"],
                "source_asset_name": FSR4_VALVE_411_ASSET["name"],
                "source_version": FSR4_VALVE_411_ASSET["version"],
            },
            {
                "name": "amdxc64.dll",
                "sha256": AMDXC64_RDNA2_ASSET["sha256"],
                "source_asset_name": AMDXC64_RDNA2_ASSET["name"],
                "source_version": AMDXC64_RDNA2_ASSET["version"],
            }
        ],
        "config_overrides": {
            "FSR.Fsr4ForceModel": "2",
            "Plugins.LoadCustomAmdxc64OnRdna2": "true",
        },
        # Applied only while the key is still "auto": a choice saved from the overlay wins.
        "config_defaults": {
            "Upscalers.Dx12Upscaler": "ffx",  # v10 name for the FFX (FSR 2.3/3.1/4) upscaler
        },
    },
    # Same Valve driver DLLs, but injected by the 0.9.4 OptiScaler whose overlay uses
    # the classic WndProc input path. For Decks where the v10 overlay ignores the
    # mouse. 0.9.4 forces the INT8 model through Fsr4ForceEnableInt8 and loads
    # amdxcffx64.dll from the game folder ("amdxcffx64 loaded from game folder").
    "rdna2-valve-411-094": {
        "label": "4.1.1 Valve RDNA2 compatibility (0.9.4 injector)",
        "dir_name": "fsr4-rdna2-valve-411-094",
        "sha256": "d0dcccc74a43c44ba435b7a369b456e0970d8a4464e4bd683119b374f2c9fb46",
        "source_asset_name": OPTISCALER_ARCHIVE_ASSET["name"],
        "source_version": OPTISCALER_ARCHIVE_ASSET["version"],
        "uses_archive_native": True,
        "extra_files": [
            {
                "name": FSR4_DRIVER_OVERRIDE_FILENAME,
                "sha256": FSR4_VALVE_411_ASSET["sha256"],
                "source_asset_name": FSR4_VALVE_411_ASSET["name"],
                "source_version": FSR4_VALVE_411_ASSET["version"],
            },
            {
                "name": "amdxc64.dll",
                "sha256": AMDXC64_RDNA2_ASSET["sha256"],
                "source_asset_name": AMDXC64_RDNA2_ASSET["name"],
                "source_version": AMDXC64_RDNA2_ASSET["version"],
            }
        ],
        "config_overrides": {
            "FSR.Fsr4ForceEnableInt8": "true",
        },
        # 0.9.4 upgrades FSR 3.1 to FSR 4 when Fsr4Update=true (set by _modify_optiscaler_ini),
        # so the game starts on FSR 4.1.1 without opening the overlay.
        "config_defaults": {
            "Upscalers.Dx12Upscaler": "fsr31",
        },
    },
}

# INI keys a variant sets that must be put back when a game leaves that variant.
VARIANT_RESET_OVERRIDES = {
    "rdna2-valve-411-pre10": {"FSR.Fsr4ForceModel": "auto", "Plugins.LoadCustomAmdxc64OnRdna2": "false"},
    "rdna2-valve-411-094": {"FSR.Fsr4ForceEnableInt8": "auto"},
}

FSR4_WATERMARK_KEY = "FSR.Fsr4EnableWatermark"

# Per-game choices made in the game view. Stored in the marker as "game_options".
# "auto" leaves the runtime's soft default in place.
DX12_UPSCALER_CHOICES = ("auto", "fsr4", "xess", "fsr22")
FRAME_GENERATION_CHOICES = ("default", "optifg")
# OptiScaler's own frame generation fed by the upscaler (for games without DLSS
# Frame Generation). Game dependent; opt-in per game.
OPTIFG_OVERRIDES = {"FrameGen.Enabled": "true", "FrameGen.FGInput": "upscaler", "FrameGen.FGOutput": "fsrfg"}
OPTIFG_RESET = {"FrameGen.Enabled": "auto", "FrameGen.FGInput": "nukems", "FrameGen.FGOutput": "nukems"}


def _normalize_game_options(options: dict | None) -> dict:
    options = options if isinstance(options, dict) else {}
    upscaler = str(options.get("dx12_upscaler") or "auto").strip().lower()
    frame_generation = str(options.get("frame_generation") or "default").strip().lower()
    return {
        "dx12_upscaler": upscaler if upscaler in DX12_UPSCALER_CHOICES else "auto",
        "frame_generation": frame_generation if frame_generation in FRAME_GENERATION_CHOICES else "default",
    }


def _dx12_upscaler_ini_value(choice: str, uses_v10_injector: bool) -> str | None:
    """INI spelling for a per-game upscaler choice (None = leave the soft default)."""
    if choice == "fsr4":
        # 0.9.4: FSR 3.1 upgraded to FSR 4 by Fsr4Update; v10 calls the same path "ffx".
        return "ffx" if uses_v10_injector else "fsr31"
    if choice in ("xess", "fsr22"):
        return choice
    return None


def _compute_bundle_fingerprint() -> str:
    """Identity of everything extract_static_optiscaler would produce."""
    parts = [
        f"layout:{BUNDLE_LAYOUT_VERSION}",
        OPTISCALER_ARCHIVE_ASSET["sha256"],
        OPTISCALER_V10_ARCHIVE_ASSET["sha256"],
        OPTISCALER_V10_INJECTOR["sha256"],
        OPTIPATCHER_ASSET["sha256"],
    ]
    for variant_id in sorted(FSR4_VARIANTS):
        variant = FSR4_VARIANTS[variant_id]
        parts.append(f"{variant_id}:{variant['dir_name']}:{variant['sha256']}")
        for extra_file in variant.get("extra_files", []):
            parts.append(f"{variant_id}:{extra_file['name']}:{extra_file['sha256']}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


BUNDLE_FINGERPRINT = _compute_bundle_fingerprint()
VARIANT_EXTRA_FILENAMES = sorted(
    {
        extra_file["name"]
        for variant in FSR4_VARIANTS.values()
        for extra_file in variant.get("extra_files", [])
    }
)

PROXY_DLL_BACKUPS = [
    "dxgi.dll",
    "winmm.dll",
    "dbghelp.dll",
    "version.dll",
    "wininet.dll",
    "winhttp.dll",
    "OptiScaler.asi",
]

VALID_DLL_NAMES = set(PROXY_DLL_BACKUPS)

INJECTOR_FILENAMES = [
    *PROXY_DLL_BACKUPS,
    "nvngx.dll",
    "_nvngx.dll",
    "nvngx-wrapper.dll",
    "dlss-enabler.dll",
    "OptiScaler.dll",
]

PATCH_CLEANUP_FILES = [
    *INJECTOR_FILENAMES,
    *VARIANT_EXTRA_FILENAMES,
    "nvapi64.dll",
    "nvapi64.dll.b",
    "nvngx.ini",
    "dlss-enabler-upscaler.dll",
    "fakenvapi.log",
    "OptiScaler.log",
    "dlssg_to_fsr3.log",
    "dlssg_to_fsr3_amd_is_better-3.0.dll",
]

PATCH_FINGERPRINT_FILES = [
    "FRAMEGEN_PATCH",
    "OptiScaler.ini",
    "fakenvapi.dll",
    "fakenvapi.ini",
    "dlssg_to_fsr3_amd_is_better.dll",
    "D3D12_Optiscaler",
]

# Game-shipped files that the bundle overwrites. They are moved to "<name>.b" before
# the copy and restored on unpatch. Every name here must also be something the
# patch actually installs, otherwise the game would run without the file.
ORIGINAL_DLL_BACKUPS = [
    "amd_fidelityfx_dx12.dll",
    "amd_fidelityfx_framegeneration_dx12.dll",
    FSR4_UPSCALER_FILENAME,
    FSR4_DRIVER_OVERRIDE_FILENAME,
    "amdxc64.dll",
    "amd_fidelityfx_vk.dll",
    # Intel XeSS titles ship these; the bundle's copies replace them.
    "libxess.dll",
    "libxess_dx11.dll",
    "libxess_fg.dll",
    "libxell.dll",
]

# d3dcompiler_47.dll is deliberately NOT in ORIGINAL_DLL_BACKUPS: the bundle never
# ships a replacement, so moving the game's copy aside only removed its shader
# compiler. Builds up to 0.17 did back it up, so keep restoring those legacy ".b"s.
LEGACY_BACKUP_FILES = ["d3dcompiler_47.dll"]

RESTORABLE_BACKUP_FILES = [
    *PROXY_DLL_BACKUPS,
    *LEGACY_BACKUP_FILES,
    *ORIGINAL_DLL_BACKUPS,
]

SUPPORT_FILES = [
    "libxess.dll",
    "libxess_dx11.dll",
    "libxess_fg.dll",
    "libxell.dll",
    "amd_fidelityfx_dx12.dll",
    "amd_fidelityfx_framegeneration_dx12.dll",
    "amd_fidelityfx_vk.dll",
    "dlssg_to_fsr3_amd_is_better.dll",
    "fakenvapi.dll",
    "fakenvapi.ini",
]

MARKER_FILENAME = "FRAMEGEN_PATCH"

BAD_EXE_SUBSTRINGS = [
    "crashreport",
    "crashreportclient",
    "eac",
    "easyanticheat",
    "beclient",
    "eosbootstrap",
    "benchmark",
    "uninstall",
    "setup",
    "launcher",
    "updater",
    "bootstrap",
    "_redist",
    "prereq",
]

LEGACY_FILES = [
    "dlssg_to_fsr3.ini",
    "dlssg_to_fsr3.log",
    "nvapi64.dll",
    "nvapi64.dll.b",
    "fakenvapi.log",
    "dlss-enabler.dll",
    "dlss-enabler-upscaler.dll",
    "dlss-enabler.log",
    "nvngx.ini",
    "nvngx-wrapper.dll",
    "_nvngx.dll",
    "dlssg_to_fsr3_amd_is_better-3.0.dll",
    "OptiScaler.asi",
    "OptiScaler.ini",
    "OptiScaler.log",
]

class Plugin:
    async def _main(self):
        decky.logger.info("Framegen plugin loaded")

    async def _unload(self):
        decky.logger.info("Framegen plugin unloaded.")
        
    def _create_renamed_copies(self, source_file, renames_dir):
        """Create renamed copies of the OptiScaler.dll file"""
        try:
            renames_dir.mkdir(exist_ok=True)
            
            rename_files = [
                "dxgi.dll",
                "winmm.dll",
                "dbghelp.dll",
                "version.dll",
                "wininet.dll",
                "winhttp.dll",
                "OptiScaler.asi"
            ]
            
            if source_file.exists():
                for rename_file in rename_files:
                    dest_file = renames_dir / rename_file
                    shutil.copy2(source_file, dest_file)
                    decky.logger.info(f"Created renamed copy: {dest_file}")
                return True
            else:
                decky.logger.error(f"Source file {source_file} does not exist")
                return False
                
        except Exception as e:
            decky.logger.error(f"Failed to create renamed copies: {e}")
            return False
    
    def _copy_launcher_scripts(self, assets_dir, extract_path):
        """Copy launcher scripts from assets directory"""
        try:
            # Copy fgmod script
            fgmod_script_src = assets_dir / "fgmod.sh"
            fgmod_script_dest = extract_path / "fgmod"
            if fgmod_script_src.exists():
                shutil.copy2(fgmod_script_src, fgmod_script_dest)
                fgmod_script_dest.chmod(0o755)
                decky.logger.info(f"Copied fgmod script to {fgmod_script_dest}")
            
            # Copy uninstaller script
            uninstaller_src = assets_dir / "fgmod-uninstaller.sh"
            uninstaller_dest = extract_path / "fgmod-uninstaller.sh"
            if uninstaller_src.exists():
                shutil.copy2(uninstaller_src, uninstaller_dest)
                uninstaller_dest.chmod(0o755)
                decky.logger.info(f"Copied uninstaller script to {uninstaller_dest}")

            # Copy optiscaler config updater script
            optiscaler_config_updater_src = assets_dir / "update-optiscaler-config.py"
            optiscaler_config_updater_dest = extract_path / "update-optiscaler-config.py"
            if optiscaler_config_updater_src.exists():
                shutil.copy2(optiscaler_config_updater_src, optiscaler_config_updater_dest)
                optiscaler_config_updater_dest.chmod(0o755)
                decky.logger.info(f"Copied update-optiscaler-config.py script to {optiscaler_config_updater_dest}")
                
            return True
        except Exception as e:
            decky.logger.error(f"Failed to copy launcher scripts: {e}")
            return False
    
    def _files_match(self, file_a: Path, file_b: Path) -> bool:
        """Byte-for-byte comparison (same answers as filecmp.cmp(shallow=False))."""
        try:
            if not (file_a.is_file() and file_b.is_file()):
                return False
            if file_a.stat().st_size != file_b.stat().st_size:
                return False
            with open(file_a, "rb") as fa, open(file_b, "rb") as fb:
                while True:
                    chunk_a = fa.read(1024 * 1024)
                    chunk_b = fb.read(1024 * 1024)
                    if chunk_a != chunk_b:
                        return False
                    if not chunk_a:
                        return True
        except Exception:
            return False

    def _bundled_proxy_candidates(self, fgmod_path: Path, dll_name: str) -> list[Path]:
        """Every file the plugin itself may have installed under a proxy DLL name."""
        candidates = [fgmod_path / "renames" / dll_name, fgmod_path / "OptiScaler.dll"]
        for variant_id in FSR4_VARIANTS:
            injector = self._fsr4_variant_injector_path(fgmod_path, variant_id)
            if injector is None:
                continue
            candidates.append(self._fsr4_variant_dir(fgmod_path, variant_id) / "renames" / dll_name)
            candidates.append(injector)
        return candidates

    def _is_bundled_proxy_copy(self, file_path: Path, fgmod_path: Path) -> bool:
        if any(self._files_match(file_path, candidate) for candidate in self._bundled_proxy_candidates(fgmod_path, file_path.name)):
            return True
        try:
            return file_path.is_file() and self._file_sha256(file_path).lower() in PREVIOUS_INJECTOR_SHA256S
        except Exception:
            return False

    def _has_patch_fingerprint(self, directory: Path) -> bool:
        return any((directory / filename).exists() for filename in PATCH_FINGERPRINT_FILES)

    def _has_plugin_injector(self, directory: Path, fgmod_path: Path) -> bool:
        """Positive evidence that this plugin installed OptiScaler here: our marker,
        or a proxy DLL that is (or was) one of our injectors. The broader fingerprint
        list also matches files a manual Nukem/fakenvapi install drops."""
        if (directory / MARKER_FILENAME).exists():
            return True
        for name in PROXY_DLL_BACKUPS:
            candidate = directory / name
            if candidate.exists() and self._is_bundled_proxy_copy(candidate, fgmod_path):
                return True
        return False

    def _backup_preexisting_proxy_files(
        self,
        directory: Path,
        fgmod_path: Path,
        managed_proxy_names: set[str] | None = None,
    ) -> list[str]:
        """Move proxy DLLs the plugin did not install to "<name>.b".

        Skipped (deleted by the cleanup loop instead): copies of any injector this
        plugin ever shipped, and the proxy names the plugin manages here (the
        marker's dll_name and the name being installed). Everything else under a
        proxy name (a version.dll mod loader, ReShade's dxgi.dll, ...) is backed up
        even when the folder already carries a patch, so a Reinstall cannot delete it.
        """
        backed_up: list[str] = []
        managed = set(managed_proxy_names or set())
        if not managed and self._has_patch_fingerprint(directory):
            # Marker-less folder that was patched before (wrapper / Advanced mode):
            # the historical default proxy is the one we installed.
            managed = {"dxgi.dll"}
        for filename in PROXY_DLL_BACKUPS:
            source = directory / filename
            backup = directory / f"{filename}.b"
            if not source.exists() or backup.exists():
                continue
            if self._is_bundled_proxy_copy(source, fgmod_path):
                continue
            if filename in managed and self._has_patch_fingerprint(directory):
                continue
            shutil.move(source, backup)
            backed_up.append(filename)
        return backed_up

    def _file_sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _read_json_file(self, path: Path) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_json_file(self, path: Path, payload: dict) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def _host_env(self) -> dict[str, str]:
        """Environment for host tools. Decky Loader is a PyInstaller bundle whose
        bootloader prepends its own libs to LD_LIBRARY_PATH; system binaries must
        not inherit that."""
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = ""
        return env

    def _archive_extract_command(self, archive_path: Path, output_dir: Path, members: list[str]) -> list[str]:
        """Build an extraction command with the first available 7z-capable tool.

        SteamOS ships a `7z` binary (p7zip on 3.6, 7-Zip's `7zip` package on 3.7+,
        which also provides `7za`); some distros only ship `7zz`; libarchive's
        `bsdtar` can also read 7z and is always present (pacman depends on it).
        """
        for tool in ("7z", "7zz", "7za"):
            if shutil.which(tool):
                return [tool, "x", "-y", "-o" + str(output_dir), str(archive_path), *members]
        if shutil.which("bsdtar"):
            return ["bsdtar", "-xf", str(archive_path), "-C", str(output_dir), *members]
        raise RuntimeError("No 7z-capable extractor found (need 7z, 7zz, 7za or bsdtar)")

    def _extract_archive(self, archive_path: Path, output_dir: Path, members: list[str] | None = None) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        extract_cmd = self._archive_extract_command(archive_path, output_dir, list(members or []))

        result = subprocess.run(
            extract_cmd,
            capture_output=True,
            text=True,
            check=False,
            env=self._host_env(),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or f"Failed to extract {archive_path.name}")

    def _verify_bundled_asset(self, path: Path, expected_sha256: str, description: str) -> str:
        actual_sha256 = self._file_sha256(path)
        if actual_sha256.lower() != expected_sha256.lower():
            raise RuntimeError(
                f"{description} hash mismatch: expected {expected_sha256}, got {actual_sha256}"
            )
        return actual_sha256

    def _install_manifest_path(self, fgmod_path: Path) -> Path:
        return fgmod_path / INSTALL_MANIFEST_FILENAME

    def _load_install_manifest(self, fgmod_path: Path) -> dict:
        return self._read_json_file(self._install_manifest_path(fgmod_path))

    def _normalize_fsr4_variant(self, fsr4_variant: str | None) -> str:
        variant = str(fsr4_variant or "").strip()
        if variant in FSR4_VARIANTS:
            return variant
        return DEFAULT_FSR4_VARIANT

    def _selected_fsr4_variant(self, fgmod_path: Path, requested_variant: str | None = None) -> str:
        normalized_requested = str(requested_variant or "").strip()
        if normalized_requested in FSR4_VARIANTS:
            return normalized_requested
        manifest = self._load_install_manifest(fgmod_path)
        manifest_variant = str(manifest.get("selected_default_variant") or "").strip()
        if manifest_variant in FSR4_VARIANTS:
            return manifest_variant
        return DEFAULT_FSR4_VARIANT

    def _fsr4_variant_info(self, fsr4_variant: str | None) -> dict:
        return FSR4_VARIANTS[self._normalize_fsr4_variant(fsr4_variant)]

    def _fsr4_variant_dir(self, fgmod_path: Path, fsr4_variant: str | None) -> Path:
        variant_id = self._normalize_fsr4_variant(fsr4_variant)
        return fgmod_path / FSR4_VARIANTS[variant_id]["dir_name"]

    def _fsr4_variant_path(self, fgmod_path: Path, fsr4_variant: str | None) -> Path:
        return self._fsr4_variant_dir(fgmod_path, fsr4_variant) / FSR4_UPSCALER_FILENAME

    def _fsr4_variant_extra_files(self, fsr4_variant: str | None) -> list[dict]:
        variant = self._fsr4_variant_info(fsr4_variant)
        return list(variant.get("extra_files") or [])

    def _fsr4_variant_extra_file_path(self, fgmod_path: Path, fsr4_variant: str | None, filename: str) -> Path:
        return self._fsr4_variant_dir(fgmod_path, fsr4_variant) / filename

    def _fsr4_variant_injector_info(self, fsr4_variant: str | None) -> dict | None:
        variant = self._fsr4_variant_info(fsr4_variant)
        injector = variant.get("injector")
        return injector if isinstance(injector, dict) else None

    def _fsr4_variant_injector_path(self, fgmod_path: Path, fsr4_variant: str | None) -> Path | None:
        injector = self._fsr4_variant_injector_info(fsr4_variant)
        if not injector:
            return None
        return self._fsr4_variant_dir(fgmod_path, fsr4_variant) / injector.get("name", "OptiScaler.dll")

    def _fsr4_variant_renamed_proxy_path(self, fgmod_path: Path, fsr4_variant: str | None, dll_name: str) -> Path | None:
        if not self._fsr4_variant_injector_info(fsr4_variant):
            return None
        return self._fsr4_variant_dir(fgmod_path, fsr4_variant) / "renames" / dll_name

    def _fsr4_variant_config_overrides(self, fsr4_variant: str | None) -> dict:
        variant = self._fsr4_variant_info(fsr4_variant)
        overrides = variant.get("config_overrides") or {}
        return dict(overrides) if isinstance(overrides, dict) else {}

    def _split_ini_override_key(self, raw_key: str) -> tuple[str | None, str]:
        key = str(raw_key).strip()
        if "." in key:
            section, section_key = key.split(".", 1)
            section = section.strip()
            section_key = section_key.strip()
            if section and section_key:
                return section, section_key
        return None, key

    def _ini_current_value(self, ini_file: Path, raw_key: str) -> str | None:
        """Value of ``Section.Key`` (or a bare key) in the INI, None when absent."""
        section, key = self._split_ini_override_key(raw_key)
        try:
            content = ini_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None
        current_section = None
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
                continue
            if not line or line.startswith(";") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == key and (section is None or current_section == section):
                return v.strip()
        return None

    def _apply_optiscaler_ini_defaults(self, ini_file: Path, defaults: dict) -> None:
        """Like overrides, but only for keys still at ``auto`` (or absent), so a value
        the user saved from the OptiScaler overlay is never replaced."""
        to_apply = {}
        for raw_key, value in (defaults or {}).items():
            current = self._ini_current_value(ini_file, str(raw_key))
            if current is None or current.lower() == "auto":
                to_apply[raw_key] = value
        if to_apply:
            self._apply_optiscaler_ini_overrides(ini_file, to_apply)

    def _reset_optiscaler_ini_defaults(self, ini_file: Path, defaults: dict) -> None:
        """Undo _apply_optiscaler_ini_defaults: only values that still equal what the
        plugin wrote go back to ``auto``."""
        to_reset = {}
        for raw_key, value in (defaults or {}).items():
            current = self._ini_current_value(ini_file, str(raw_key))
            if current is not None and current.lower() == str(value).lower():
                to_reset[raw_key] = "auto"
        if to_reset:
            self._apply_optiscaler_ini_overrides(ini_file, to_reset)

    def _apply_optiscaler_ini_overrides(self, ini_file: Path, overrides: dict) -> bool:
        if not overrides:
            return True
        try:
            content = ini_file.read_text(encoding="utf-8", errors="replace")
            newline = "\r\n" if "\r\n" in content else "\n"
            lines = content.splitlines(keepends=True)
            section_pattern = re.compile(r"^\s*\[(?P<section>[^\]]+)\]\s*$")

            def ensure_trailing_newline() -> None:
                if lines and not lines[-1].endswith(("\n", "\r")):
                    lines[-1] += newline

            def upsert(section: str | None, key: str, value: str) -> None:
                replacement = f"{key}={value}"
                key_pattern = re.compile(rf"^(\s*{re.escape(key)}\s*)=.*$")

                if section is None:
                    for idx, line in enumerate(lines):
                        if key_pattern.match(line):
                            line_ending = "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else newline)
                            lines[idx] = f"{replacement}{line_ending}"
                            return
                    ensure_trailing_newline()
                    lines.append(f"{replacement}{newline}")
                    return

                in_section = False
                insert_at = None
                for idx, line in enumerate(lines):
                    match = section_pattern.match(line.strip())
                    if match:
                        if in_section:
                            insert_at = idx
                            break
                        if match.group("section") == section:
                            in_section = True
                            continue
                    if in_section and key_pattern.match(line):
                        line_ending = "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else newline)
                        lines[idx] = f"{replacement}{line_ending}"
                        return

                if in_section:
                    if insert_at is None:
                        ensure_trailing_newline()
                        insert_at = len(lines)
                    lines.insert(insert_at, f"{replacement}{newline}")
                    return

                ensure_trailing_newline()
                if lines and lines[-1].strip():
                    lines.append(newline)
                lines.append(f"[{section}]{newline}")
                lines.append(f"{replacement}{newline}")

            for raw_key, raw_value in overrides.items():
                section, key = self._split_ini_override_key(str(raw_key))
                value = str(raw_value).strip()
                if key:
                    upsert(section, key, value)

            ini_file.write_text("".join(lines), encoding="utf-8")
            return True
        except Exception as exc:
            decky.logger.error(f"Failed to apply OptiScaler.ini overrides to {ini_file}: {exc}")
            return False

    def _sync_variant_root_extra_files(self, fgmod_path: Path, fsr4_variant: str | None) -> None:
        selected_extra_files = {extra_file["name"]: extra_file for extra_file in self._fsr4_variant_extra_files(fsr4_variant)}
        for filename in VARIANT_EXTRA_FILENAMES:
            root_path = fgmod_path / filename
            if filename not in selected_extra_files:
                if root_path.exists():
                    root_path.unlink()
                continue
            source_path = self._fsr4_variant_extra_file_path(fgmod_path, fsr4_variant, filename)
            if not source_path.exists():
                raise FileNotFoundError(f"Prepared FSR4 variant extra file missing: {source_path}")
            shutil.copy2(source_path, root_path)

    def _activate_default_fsr4_variant(self, fgmod_path: Path, fsr4_variant: str | None) -> str:
        variant_id = self._normalize_fsr4_variant(fsr4_variant)
        variant_path = self._fsr4_variant_path(fgmod_path, variant_id)
        if not variant_path.exists():
            raise FileNotFoundError(f"Prepared FSR4 variant missing: {variant_path}")
        shutil.copy2(variant_path, fgmod_path / FSR4_UPSCALER_FILENAME)
        self._sync_variant_root_extra_files(fgmod_path, variant_id)
        return variant_id

    def _detect_fsr4_variant(
        self,
        directory: Path,
        upscaler_sha256: str | None,
        injector_path: Path | None = None,
        preferred: str | None = None,
        file_cache: dict | None = None,
    ) -> str | None:
        """Identify the runtime a game folder carries from its upscaler and driver DLLs.
        Two Valve RDNA2 variants share those files and differ only in the injector,
        so the proxy DLL (``injector_path``) breaks the tie; when its bytes are not a
        known injector, the marker's recorded variant (``preferred``) wins."""
        matches: list[str] = []
        for variant_id, variant in FSR4_VARIANTS.items():
            extra_files = list(variant.get("extra_files") or [])
            if not extra_files:
                continue
            if not upscaler_sha256 or str(variant.get("sha256") or "").lower() != str(upscaler_sha256).lower():
                continue
            all_match = True
            for extra_file in extra_files:
                file_path = directory / extra_file["name"]
                if not file_path.exists() or self._cached_sha256(file_path, file_cache) != extra_file["sha256"].lower():
                    all_match = False
                    break
            if all_match:
                matches.append(variant_id)
        if len(matches) == 1:
            return matches[0]
        if matches:
            injector_sha = None
            if injector_path is not None and injector_path.is_file():
                try:
                    injector_sha = self._cached_sha256(injector_path, file_cache)
                except Exception:
                    injector_sha = None
            with_injector = [v for v in matches if self._fsr4_variant_injector_info(v)]
            without_injector = [v for v in matches if not self._fsr4_variant_injector_info(v)]
            for variant_id in with_injector:
                expected = self._fsr4_variant_injector_info(variant_id)["sha256"].lower()
                if injector_sha in (expected, *PREVIOUS_INJECTOR_SHA256S):
                    return variant_id
            if preferred in matches:
                return preferred
            if injector_sha is not None and without_injector:
                return without_injector[0]
            return matches[0]

        if not upscaler_sha256:
            return None
        normalized_sha = str(upscaler_sha256).lower()
        for variant_id, variant in FSR4_VARIANTS.items():
            if variant.get("extra_files"):
                continue
            if str(variant.get("sha256") or "").lower() == normalized_sha:
                return variant_id
        return None

    def _fgmod_version(self, fgmod_path: Path) -> str | None:
        manifest = self._load_install_manifest(fgmod_path)
        optiscaler = manifest.get("optiscaler") if isinstance(manifest, dict) else None
        if isinstance(optiscaler, dict) and optiscaler.get("version"):
            return str(optiscaler.get("version"))
        version_file = fgmod_path / VERSION_FILENAME
        try:
            if version_file.exists():
                return version_file.read_text(encoding="utf-8").strip() or None
        except Exception:
            return None
        return None

    def _managed_support_candidate_paths(self, fgmod_path: Path, filename: str) -> list[Path]:
        candidates: list[Path] = []
        if filename == FSR4_UPSCALER_FILENAME:
            candidates.append(fgmod_path / FSR4_UPSCALER_FILENAME)
            for variant_id in FSR4_VARIANTS:
                candidates.append(self._fsr4_variant_path(fgmod_path, variant_id))
        else:
            candidates.append(fgmod_path / filename)
            for variant_id in FSR4_VARIANTS:
                for extra_file in self._fsr4_variant_extra_files(variant_id):
                    if extra_file["name"] == filename:
                        candidates.append(self._fsr4_variant_extra_file_path(fgmod_path, variant_id, filename))
        unique: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            key = str(candidate)
            if key not in seen:
                unique.append(candidate)
                seen.add(key)
        return unique

    def _is_managed_support_file(self, path: Path, fgmod_path: Path) -> bool:
        if not path.exists():
            return False
        for candidate in self._managed_support_candidate_paths(fgmod_path, path.name):
            if self._files_match(path, candidate):
                return True
        return False

    def _migrate_optiscaler_ini(self, ini_file):
        """Migrate pre-v0.9-final OptiScaler.ini: replace FGType with FGInput + FGOutput.

        v0.9-final split the single FGType key into separate FGInput and FGOutput keys.
        Games already patched with an older build will have FGType=<value> in their
        per-game INI but no FGInput/FGOutput entries, causing the new DLL to silently
        fall back to nofg.  This migration runs at patch-time and at every fgmod.sh
        launch so users never have to manually touch their INI.
        """
        try:
            if not ini_file.exists():
                return False

            with open(ini_file, 'r') as f:
                content = f.read()

            fg_type_match = re.search(r'^FGType\s*=\s*(\S+)', content, re.MULTILINE)
            if not fg_type_match:
                return True  # Nothing to migrate

            fg_value = fg_type_match.group(1)

            if re.search(r'^FGInput\s*=', content, re.MULTILINE):
                # FGInput already present (INI already in v0.9-final format);
                # just remove the now-unknown FGType line.
                content = re.sub(r'^FGType\s*=\s*\S+\n?', '', content, flags=re.MULTILINE)
                decky.logger.info(f"Removed stale FGType from {ini_file} (FGInput already present)")
            else:
                # Replace the single FGType=X line with FGInput=X then FGOutput=X
                content = re.sub(
                    r'^FGType\s*=\s*\S+',
                    f'FGInput={fg_value}\nFGOutput={fg_value}',
                    content,
                    flags=re.MULTILINE
                )
                decky.logger.info(f"Migrated FGType={fg_value} → FGInput={fg_value}, FGOutput={fg_value} in {ini_file}")

            with open(ini_file, 'w') as f:
                f.write(content)
            return True
        except Exception as e:
            decky.logger.error(f"Failed to migrate OptiScaler.ini: {e}")
            return False

    def _needs_v10_fg_downgrade(self, ini_file: Path) -> bool:
        """True if the INI carries the v10-only FG vocabulary that 0.9.4 rejects.

        The v10 injector (Valve RDNA2 runtime) saves ``FGInput=NvngxFG`` plus
        ``FGNvngxReplacement=Nukems`` from its overlay. The 0.9.4 injector used by
        the other runtimes does not know ``nvngxfg`` and silently falls back to
        no frame generation. ``FGInput=nukems`` is the exact 0.9.4 spelling and is
        still accepted by v10, so the reverse mapping is lossless.
        """
        try:
            content = ini_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return False
        if not re.search(r"^\s*FGInput\s*=\s*nvngxfg\s*$", content, re.IGNORECASE | re.MULTILINE):
            return False
        replacement = re.search(r"^\s*FGNvngxReplacement\s*=\s*(\S+)\s*$", content, re.IGNORECASE | re.MULTILINE)
        return replacement is None or replacement.group(1).lower() in ("nukems", "auto")

    def _disable_hq_font_auto(self, ini_file):
        """Disable the new HQ font auto mode to avoid missing font assertions on Wine/Proton."""
        try:
            if not ini_file.exists():
                decky.logger.warning(f"OptiScaler.ini not found at {ini_file}")
                return False

            with open(ini_file, 'r') as f:
                content = f.read()

            updated_content = re.sub(r'UseHQFont\s*=\s*auto', 'UseHQFont=false', content)
            if updated_content != content:
                with open(ini_file, 'w') as f:
                    f.write(updated_content)
                decky.logger.info("Set UseHQFont=false to avoid missing font assertions")

            return True
        except Exception as e:
            decky.logger.error(f"Failed to update HQ font setting in OptiScaler.ini: {e}")
            return False

    def _modify_optiscaler_ini(self, ini_file):
        """Modify OptiScaler.ini to set FG defaults, ASI plugin settings, and safe font defaults."""
        try:
            if ini_file.exists():
                with open(ini_file, 'r') as f:
                    content = f.read()
                
                # Replace FGInput=auto with FGInput=nukems (final v0.9+ split FGType into FGInput/FGOutput)
                updated_content = re.sub(r'FGInput\s*=\s*auto', 'FGInput=nukems', content)

                # Replace FGOutput=auto with FGOutput=nukems
                updated_content = re.sub(r'FGOutput\s*=\s*auto', 'FGOutput=nukems', updated_content)
                
                # Replace Fsr4Update=auto with Fsr4Update=true
                updated_content = re.sub(r'Fsr4Update\s*=\s*auto', 'Fsr4Update=true', updated_content)
                
                # Replace LoadAsiPlugins=auto with LoadAsiPlugins=true
                updated_content = re.sub(r'LoadAsiPlugins\s*=\s*auto', 'LoadAsiPlugins=true', updated_content)

                # Disable new HQ font auto mode to avoid missing font assertions on Proton
                updated_content = re.sub(r'UseHQFont\s*=\s*auto', 'UseHQFont=false', updated_content)
                
                with open(ini_file, 'w') as f:
                    f.write(updated_content)
                
                decky.logger.info(
                    "Modified OptiScaler.ini to set FGInput=nukems, FGOutput=nukems, Fsr4Update=true, "
                    "LoadAsiPlugins=true, UseHQFont=false (the v10 injector maps FGInput=nukems to "
                    "nvngxfg+Nukems replacement and ignores FGOutput/Fsr4Update)"
                )
                return True
            else:
                decky.logger.warning(f"OptiScaler.ini not found at {ini_file}")
                return False
        except Exception as e:
            decky.logger.error(f"Failed to modify OptiScaler.ini: {e}")
            return False

    async def extract_static_optiscaler(self, selected_default_variant: str = DEFAULT_FSR4_VARIANT) -> dict:
        """Prepare the shared ~/fgmod bundle with all bundled FSR4 runtime variants."""
        try:
            decky.logger.info("Starting extract_static_optiscaler method")

            bin_path = Path(decky.DECKY_PLUGIN_DIR) / "bin"
            extract_path = Path(decky.HOME) / "fgmod"
            assets_dir = Path(decky.DECKY_PLUGIN_DIR) / "assets"
            selected_default_variant = self._normalize_fsr4_variant(selected_default_variant)

            if not bin_path.exists():
                return {"status": "error", "message": f"Bin directory not found: {bin_path}"}

            optiscaler_archive = bin_path / OPTISCALER_ARCHIVE_ASSET["name"]
            fsr4_int8_src = bin_path / FSR4_INT8_ASSET["name"]
            fsr4_official_411_src = bin_path / FSR4_OFFICIAL_411_ASSET["name"]
            fsr4_valve_411_src = bin_path / FSR4_VALVE_411_ASSET["name"]
            amdxc64_rdna2_src = bin_path / AMDXC64_RDNA2_ASSET["name"]
            optiscaler_v10_archive = bin_path / OPTISCALER_V10_ARCHIVE_ASSET["name"]
            optipatcher_src = bin_path / OPTIPATCHER_ASSET["name"]
            for required_path, asset in [
                (optiscaler_archive, OPTISCALER_ARCHIVE_ASSET),
                (fsr4_int8_src, FSR4_INT8_ASSET),
                (fsr4_official_411_src, FSR4_OFFICIAL_411_ASSET),
                (fsr4_valve_411_src, FSR4_VALVE_411_ASSET),
                (amdxc64_rdna2_src, AMDXC64_RDNA2_ASSET),
                (optiscaler_v10_archive, OPTISCALER_V10_ARCHIVE_ASSET),
                (optipatcher_src, OPTIPATCHER_ASSET),
            ]:
                if not required_path.exists():
                    return {
                        "status": "error",
                        "message": f"Required bundled asset missing: {asset['name']}",
                    }
                self._verify_bundled_asset(required_path, asset["sha256"], asset["name"])

            # Preferences survive a rebuild.
            previous_manifest = self._load_install_manifest(extract_path)
            if extract_path.exists():
                shutil.rmtree(extract_path)
            extract_path.mkdir(parents=True, exist_ok=True)

            self._extract_archive(optiscaler_archive, extract_path)

            source_file = extract_path / "OptiScaler.dll"
            renames_dir = extract_path / "renames"
            if not self._create_renamed_copies(source_file, renames_dir):
                return {"status": "error", "message": "Failed to prepare renamed OptiScaler proxies."}

            if not self._copy_launcher_scripts(assets_dir, extract_path):
                return {"status": "error", "message": "Failed to copy launcher scripts."}

            plugins_dir = extract_path / "plugins"
            plugins_dir.mkdir(parents=True, exist_ok=True)
            optipatcher_dst = plugins_dir / "OptiPatcher.asi"
            shutil.copy2(optipatcher_src, optipatcher_dst)
            optipatcher_sha256 = self._verify_bundled_asset(
                optipatcher_dst,
                OPTIPATCHER_ASSET["sha256"],
                "Prepared OptiPatcher plugin",
            )

            ini_file = extract_path / "OptiScaler.ini"
            self._modify_optiscaler_ini(ini_file)

            native_upscaler_root = extract_path / FSR4_UPSCALER_FILENAME
            native_upscaler_sha256 = self._verify_bundled_asset(
                native_upscaler_root,
                FSR4_VARIANTS["rdna4-native"]["sha256"],
                "Archive-native FSR4 upscaler",
            )

            rdna4_dir = extract_path / FSR4_VARIANTS["rdna4-native"]["dir_name"]
            rdna4_dir.mkdir(parents=True, exist_ok=True)
            rdna4_upscaler = rdna4_dir / FSR4_UPSCALER_FILENAME
            shutil.copy2(native_upscaler_root, rdna4_upscaler)
            self._verify_bundled_asset(
                rdna4_upscaler,
                FSR4_VARIANTS["rdna4-native"]["sha256"],
                "Prepared rdna4-native FSR4 upscaler",
            )

            official_411_dir = extract_path / FSR4_VARIANTS["rdna34-official-411"]["dir_name"]
            official_411_dir.mkdir(parents=True, exist_ok=True)
            official_411_upscaler = official_411_dir / FSR4_UPSCALER_FILENAME
            shutil.copy2(native_upscaler_root, official_411_upscaler)
            self._verify_bundled_asset(
                official_411_upscaler,
                FSR4_VARIANTS["rdna34-official-411"]["sha256"],
                "Prepared rdna34-official-411 FSR4 upscaler",
            )
            self._verify_bundled_asset(
                fsr4_official_411_src,
                FSR4_OFFICIAL_411_ASSET["sha256"],
                "Bundled rdna34-official-411 driver override",
            )
            official_411_driver = official_411_dir / FSR4_DRIVER_OVERRIDE_FILENAME
            shutil.copy2(fsr4_official_411_src, official_411_driver)
            self._verify_bundled_asset(
                official_411_driver,
                FSR4_OFFICIAL_411_ASSET["sha256"],
                "Prepared rdna34-official-411 driver override",
            )

            rdna2_valve_dir = extract_path / FSR4_VARIANTS["rdna2-valve-411-pre10"]["dir_name"]
            rdna2_valve_dir.mkdir(parents=True, exist_ok=True)
            rdna2_valve_upscaler = rdna2_valve_dir / FSR4_UPSCALER_FILENAME
            shutil.copy2(native_upscaler_root, rdna2_valve_upscaler)
            self._verify_bundled_asset(
                rdna2_valve_upscaler,
                FSR4_VARIANTS["rdna2-valve-411-pre10"]["sha256"],
                "Prepared rdna2-valve-411-pre10 FSR4 upscaler",
            )
            self._verify_bundled_asset(
                fsr4_valve_411_src,
                FSR4_VALVE_411_ASSET["sha256"],
                "Bundled rdna2-valve-411-pre10 driver override",
            )
            rdna2_valve_driver = rdna2_valve_dir / FSR4_DRIVER_OVERRIDE_FILENAME
            shutil.copy2(fsr4_valve_411_src, rdna2_valve_driver)
            self._verify_bundled_asset(
                rdna2_valve_driver,
                FSR4_VALVE_411_ASSET["sha256"],
                "Prepared rdna2-valve-411-pre10 driver override",
            )
            self._verify_bundled_asset(
                amdxc64_rdna2_src,
                AMDXC64_RDNA2_ASSET["sha256"],
                "Bundled rdna2-valve-411-pre10 amdxc64 override",
            )
            rdna2_valve_amdxc64 = rdna2_valve_dir / "amdxc64.dll"
            shutil.copy2(amdxc64_rdna2_src, rdna2_valve_amdxc64)
            self._verify_bundled_asset(
                rdna2_valve_amdxc64,
                AMDXC64_RDNA2_ASSET["sha256"],
                "Prepared rdna2-valve-411-pre10 amdxc64 override",
            )
            # Pull only the root OptiScaler.dll out of the v10 nightly archive; the
            # variant keeps using the 0.9.4 support DLLs (identical upscaler/FG/XeSS
            # binaries) that are already in ~/fgmod.
            rdna2_valve_injector = rdna2_valve_dir / OPTISCALER_V10_INJECTOR["name"]
            self._extract_archive(
                optiscaler_v10_archive,
                rdna2_valve_dir,
                members=[OPTISCALER_V10_INJECTOR["name"]],
            )
            if not rdna2_valve_injector.exists():
                return {
                    "status": "error",
                    "message": f"{OPTISCALER_V10_INJECTOR['name']} missing from {OPTISCALER_V10_ARCHIVE_ASSET['name']}",
                }
            self._verify_bundled_asset(
                rdna2_valve_injector,
                OPTISCALER_V10_INJECTOR["sha256"],
                "Prepared rdna2-valve-411-pre10 OptiScaler v10 injector",
            )
            if not self._create_renamed_copies(rdna2_valve_injector, rdna2_valve_dir / "renames"):
                return {"status": "error", "message": "Failed to prepare renamed OptiScaler v10 proxies."}

            rdna2_valve_094_dir = extract_path / FSR4_VARIANTS["rdna2-valve-411-094"]["dir_name"]
            rdna2_valve_094_dir.mkdir(parents=True, exist_ok=True)
            for src, name, expected, what in [
                (native_upscaler_root, FSR4_UPSCALER_FILENAME, FSR4_VARIANTS["rdna2-valve-411-094"]["sha256"], "FSR4 upscaler"),
                (fsr4_valve_411_src, FSR4_DRIVER_OVERRIDE_FILENAME, FSR4_VALVE_411_ASSET["sha256"], "driver override"),
                (amdxc64_rdna2_src, "amdxc64.dll", AMDXC64_RDNA2_ASSET["sha256"], "amdxc64 override"),
            ]:
                dst = rdna2_valve_094_dir / name
                shutil.copy2(src, dst)
                self._verify_bundled_asset(dst, expected, f"Prepared rdna2-valve-411-094 {what}")

            rdna23_dir = extract_path / FSR4_VARIANTS["rdna23-int8"]["dir_name"]
            rdna23_dir.mkdir(parents=True, exist_ok=True)
            self._verify_bundled_asset(
                fsr4_int8_src,
                FSR4_VARIANTS["rdna23-int8"]["sha256"],
                "Bundled rdna23-int8 FSR4 upscaler",
            )
            shutil.copy2(fsr4_int8_src, rdna23_dir / FSR4_UPSCALER_FILENAME)
            self._verify_bundled_asset(
                rdna23_dir / FSR4_UPSCALER_FILENAME,
                FSR4_VARIANTS["rdna23-int8"]["sha256"],
                "Prepared rdna23-int8 FSR4 upscaler",
            )

            selected_default_variant = self._activate_default_fsr4_variant(extract_path, selected_default_variant)
            active_upscaler_sha256 = self._file_sha256(extract_path / FSR4_UPSCALER_FILENAME)

            version_file = extract_path / VERSION_FILENAME
            version_file.write_text(OPTISCALER_ARCHIVE_ASSET["version"], encoding="utf-8")

            install_manifest = {
                "schema_version": 1,
                "installed_at": datetime.now(timezone.utc).isoformat(),
                "optiscaler": {
                    "asset_name": OPTISCALER_ARCHIVE_ASSET["name"],
                    "version": OPTISCALER_ARCHIVE_ASSET["version"],
                    "sha256": OPTISCALER_ARCHIVE_ASSET["sha256"],
                    "native_upscaler_sha256": native_upscaler_sha256,
                },
                "optipatcher": {
                    "asset_name": OPTIPATCHER_ASSET["name"],
                    "version": OPTIPATCHER_ASSET["version"],
                    "sha256": optipatcher_sha256,
                    "target_path": str(optipatcher_dst.relative_to(extract_path)),
                },
                "fsr4_variants": {
                    variant_id: {
                        "label": variant["label"],
                        "dir_name": variant["dir_name"],
                        "path": str((Path(variant["dir_name"]) / FSR4_UPSCALER_FILENAME).as_posix()),
                        "sha256": variant["sha256"],
                        "source_asset_name": variant["source_asset_name"],
                        "source_version": variant["source_version"],
                        "uses_archive_native": bool(variant["uses_archive_native"]),
                        "injector": (
                            {
                                "name": variant["injector"]["name"],
                                "sha256": variant["injector"]["sha256"],
                                "source_asset_name": variant["injector"]["source_asset_name"],
                                "source_version": variant["injector"]["source_version"],
                                "path": str((Path(variant["dir_name"]) / variant["injector"]["name"]).as_posix()),
                            }
                            if isinstance(variant.get("injector"), dict)
                            else None
                        ),
                        "config_overrides": dict(variant.get("config_overrides") or {}),
                        "extra_files": [
                            {
                                "name": extra_file["name"],
                                "sha256": extra_file["sha256"],
                                "source_asset_name": extra_file["source_asset_name"],
                                "source_version": extra_file["source_version"],
                                "path": str((Path(variant["dir_name"]) / extra_file["name"]).as_posix()),
                            }
                            for extra_file in variant.get("extra_files", [])
                        ],
                    }
                    for variant_id, variant in FSR4_VARIANTS.items()
                },
                "selected_default_variant": selected_default_variant,
                "active_root_upscaler": {
                    "path": FSR4_UPSCALER_FILENAME,
                    "sha256": active_upscaler_sha256,
                    "variant": selected_default_variant,
                },
                "bundle_fingerprint": BUNDLE_FINGERPRINT,
                "fsr4_watermark": bool(previous_manifest.get("fsr4_watermark")),
            }
            self._write_json_file(self._install_manifest_path(extract_path), install_manifest)

            return {
                "status": "success",
                "message": f"Successfully extracted OptiScaler {OPTISCALER_ARCHIVE_ASSET['version']} to ~/fgmod",
                "version": OPTISCALER_ARCHIVE_ASSET["version"],
                "selected_default_variant": selected_default_variant,
                "selected_default_variant_label": FSR4_VARIANTS[selected_default_variant]["label"],
            }
        except Exception as e:
            decky.logger.error(f"Extract failed with exception: {str(e)}")
            import traceback
            decky.logger.error(f"Traceback: {traceback.format_exc()}")
            return {"status": "error", "message": f"Extract failed: {str(e)}"}

    async def run_uninstall_fgmod(self) -> dict:
        try:
            # Remove fgmod directory
            fgmod_path = Path(decky.HOME) / "fgmod"
            
            if fgmod_path.exists():
                shutil.rmtree(fgmod_path)
                decky.logger.info(f"Removed directory: {fgmod_path}")
                return {
                    "status": "success", 
                    "output": "Successfully removed fgmod directory"
                }
            else:
                return {
                    "status": "success", 
                    "output": "No fgmod directory found to remove"
                }
            
        except Exception as e:
            decky.logger.error(f"Uninstall error: {str(e)}")
            return {
                "status": "error", 
                "message": f"Uninstall failed: {str(e)}", 
                "output": str(e)
            }

    async def set_default_fsr4_variant(self, selected_default_variant: str = DEFAULT_FSR4_VARIANT) -> dict:
        try:
            fgmod_path = Path(decky.HOME) / "fgmod"
            if not fgmod_path.exists():
                return {"status": "error", "message": "OptiScaler bundle not installed. Run Install first."}

            selected_default_variant = self._normalize_fsr4_variant(selected_default_variant)
            manifest = self._load_install_manifest(fgmod_path)
            if not manifest:
                return {"status": "error", "message": "Install manifest missing. Reinstall OptiScaler."}

            selected_default_variant = self._activate_default_fsr4_variant(fgmod_path, selected_default_variant)
            active_upscaler_sha256 = self._file_sha256(fgmod_path / FSR4_UPSCALER_FILENAME)
            manifest["selected_default_variant"] = selected_default_variant
            manifest["active_root_upscaler"] = {
                "path": FSR4_UPSCALER_FILENAME,
                "sha256": active_upscaler_sha256,
                "variant": selected_default_variant,
            }
            manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write_json_file(self._install_manifest_path(fgmod_path), manifest)
            return {
                "status": "success",
                "output": f"Default FSR4 runtime switched to {FSR4_VARIANTS[selected_default_variant]['label']}.",
                "version": self._fgmod_version(fgmod_path),
                "selected_default_variant": selected_default_variant,
                "selected_default_variant_label": FSR4_VARIANTS[selected_default_variant]["label"],
            }
        except Exception as e:
            decky.logger.error(f"Failed to switch default FSR4 runtime: {e}")
            return {"status": "error", "message": f"Failed to switch default FSR4 runtime: {e}"}

    def _bundle_is_current(self, fgmod_path: Path) -> bool:
        """True when ~/fgmod was produced by this exact asset set and layout and every
        prepared file is still there, so Setup can skip the 110 MB re-extraction."""
        manifest = self._load_install_manifest(fgmod_path)
        if str(manifest.get("bundle_fingerprint") or "") != BUNDLE_FINGERPRINT:
            return False
        return self._bundle_files_present(fgmod_path)

    async def run_install_fgmod(self, selected_default_variant: str = DEFAULT_FSR4_VARIANT) -> dict:
        try:
            decky.logger.info("Starting OptiScaler installation from static bundle")
            selected_default_variant = self._normalize_fsr4_variant(selected_default_variant)
            fgmod_path = Path(decky.HOME) / "fgmod"

            if self._bundle_is_current(fgmod_path):
                decky.logger.info("Existing ~/fgmod matches this build; refreshing scripts and runtime only")
                assets_dir = Path(decky.DECKY_PLUGIN_DIR) / "assets"
                if not self._copy_launcher_scripts(assets_dir, fgmod_path):
                    return {"status": "error", "message": "Failed to refresh launcher scripts."}
                switch_result = await self.set_default_fsr4_variant(selected_default_variant)
                if switch_result.get("status") != "success":
                    return switch_result
                return {
                    "status": "success",
                    "output": (
                        f"OptiScaler {OPTISCALER_ARCHIVE_ASSET['version']} bundle verified; "
                        f"default runtime {FSR4_VARIANTS[selected_default_variant]['label']}."
                    ),
                    "version": OPTISCALER_ARCHIVE_ASSET["version"],
                    "selected_default_variant": selected_default_variant,
                    "selected_default_variant_label": FSR4_VARIANTS[selected_default_variant]["label"],
                }

            extract_result = await self.extract_static_optiscaler(selected_default_variant)
            if extract_result["status"] != "success":
                return {
                    "status": "error",
                    "message": f"OptiScaler extraction failed: {extract_result.get('message', 'Unknown error')}"
                }

            return {
                "status": "success",
                "output": (
                    "Successfully installed OptiScaler "
                    f"{extract_result.get('version', OPTISCALER_ARCHIVE_ASSET['version'])} "
                    f"with {extract_result.get('selected_default_variant_label', FSR4_VARIANTS[selected_default_variant]['label'])}."
                ),
                "version": extract_result.get("version", OPTISCALER_ARCHIVE_ASSET["version"]),
                "selected_default_variant": extract_result.get("selected_default_variant", selected_default_variant),
                "selected_default_variant_label": extract_result.get(
                    "selected_default_variant_label",
                    FSR4_VARIANTS[selected_default_variant]["label"],
                ),
            }

        except Exception as e:
            decky.logger.error(f"Unexpected error during installation: {str(e)}")
            return {
                "status": "error",
                "message": f"Installation failed: {str(e)}"
            }

    async def set_fsr4_watermark(self, enabled: bool = False) -> dict:
        """Remember whether patched games should show AMD's FSR 4 watermark."""
        try:
            fgmod_path = Path(decky.HOME) / "fgmod"
            manifest = self._load_install_manifest(fgmod_path)
            if not manifest:
                return {"status": "error", "message": "OptiScaler bundle not installed. Run Setup first."}
            manifest["fsr4_watermark"] = bool(enabled)
            manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write_json_file(self._install_manifest_path(fgmod_path), manifest)
            return {"status": "success", "fsr4_watermark": bool(enabled)}
        except Exception as exc:
            decky.logger.error(f"Failed to store watermark preference: {exc}")
            return {"status": "error", "message": str(exc)}

    async def check_fgmod_path(self) -> dict:
        path = Path(decky.HOME) / "fgmod"
        if not path.exists() or not self._bundle_files_present(path):
            return {"exists": False}

        manifest = self._load_install_manifest(path)
        selected_variant = self._selected_fsr4_variant(path)
        outdated_variants = self._outdated_injector_variants(manifest)
        return {
            "exists": True,
            "version": self._fgmod_version(path),
            "selected_fsr4_variant": selected_variant,
            "selected_fsr4_variant_label": FSR4_VARIANTS[selected_variant]["label"],
            "install_manifest_present": bool(manifest),
            # A ~/fgmod prepared by an older plugin build still carries the old
            # injector; only re-running Setup replaces it. Cheap JSON-only check
            # because the frontend polls this every few seconds.
            "bundle_outdated": bool(outdated_variants),
            "outdated_variants": outdated_variants,
            "fsr4_watermark": bool(manifest.get("fsr4_watermark")),
        }

    def _bundle_files_present(self, path: Path) -> bool:
        required_files = [
            "OptiScaler.dll",
            "OptiScaler.ini",
            "dlssg_to_fsr3_amd_is_better.dll",
            "fakenvapi.dll",
            "fakenvapi.ini",
            "amd_fidelityfx_dx12.dll",
            "amd_fidelityfx_framegeneration_dx12.dll",
            FSR4_UPSCALER_FILENAME,
            "amd_fidelityfx_vk.dll",
            "libxess.dll",
            "libxess_dx11.dll",
            "libxess_fg.dll",
            "libxell.dll",
            "fgmod",
            "fgmod-uninstaller.sh",
            "update-optiscaler-config.py",
            INSTALL_MANIFEST_FILENAME,
        ]

        for file_name in required_files:
            if not path.joinpath(file_name).exists():
                return False

        plugins_dir = path / "plugins"
        if not plugins_dir.exists() or not (plugins_dir / "OptiPatcher.asi").exists():
            return False

        for variant_id, variant in FSR4_VARIANTS.items():
            variant_dir = path / variant["dir_name"]
            variant_path = variant_dir / FSR4_UPSCALER_FILENAME
            if not variant_path.exists():
                return False
            injector = variant.get("injector")
            if isinstance(injector, dict):
                if not (variant_dir / injector.get("name", "OptiScaler.dll")).exists():
                    return False
                if not (variant_dir / "renames" / "dxgi.dll").exists():
                    return False
            for extra_file in variant.get("extra_files", []):
                if not (variant_dir / extra_file["name"]).exists():
                    return False
        return True

    def _outdated_injector_variants(self, manifest: dict) -> list[str]:
        recorded = manifest.get("fsr4_variants") if isinstance(manifest, dict) else None
        recorded = recorded if isinstance(recorded, dict) else {}
        outdated: list[str] = []
        for variant_id, variant in FSR4_VARIANTS.items():
            injector = variant.get("injector")
            if not isinstance(injector, dict):
                continue
            recorded_injector = (recorded.get(variant_id) or {}).get("injector") or {}
            if str(recorded_injector.get("sha256") or "").lower() != injector["sha256"].lower():
                outdated.append(variant_id)
        return outdated

    def _installed_injector_is_current(self, fgmod_path: Path, fsr4_variant: str) -> bool:
        """Verify the prepared variant injector on disk is the one this build expects."""
        injector = self._fsr4_variant_injector_info(fsr4_variant)
        if not injector:
            return True
        injector_path = self._fsr4_variant_injector_path(fgmod_path, fsr4_variant)
        if injector_path is None or not injector_path.exists():
            return False
        return self._file_sha256(injector_path).lower() == injector["sha256"].lower()

    def _resolve_target_directory(self, directory: str) -> Path:
        decky.logger.info(f"Resolving target directory: {directory}")
        target = Path(directory).expanduser()
        if not target.exists():
            raise FileNotFoundError(f"Target directory does not exist: {directory}")
        if not target.is_dir():
            raise NotADirectoryError(f"Target path is not a directory: {directory}")
        if not os.access(target, os.W_OK | os.X_OK):
            raise PermissionError(f"Insufficient permissions for {directory}")
        decky.logger.info(f"Resolved directory {directory} to absolute path {target}")
        return target

    def _manual_patch_directory_impl(
        self,
        directory: Path,
        dll_name: str = "dxgi.dll",
        fsr4_variant: str | None = None,
        allow_managed_support_cleanup: bool = False,
        game_options: dict | None = None,
    ) -> dict:
        fgmod_path = Path(decky.HOME) / "fgmod"
        if not fgmod_path.exists():
            return {
                "status": "error",
                "message": "OptiScaler bundle not installed. Run Install first.",
            }
        game_options = _normalize_game_options(game_options)

        optiscaler_dll = fgmod_path / "OptiScaler.dll"
        if not optiscaler_dll.exists():
            return {
                "status": "error",
                "message": "OptiScaler.dll not found in ~/fgmod. Reinstall OptiScaler.",
            }

        preserve_ini = True
        previous_marker_metadata = self._read_marker(directory / MARKER_FILENAME)
        previous_variant = str(previous_marker_metadata.get("fsr4_variant") or "").strip()
        selected_variant = self._selected_fsr4_variant(fgmod_path, fsr4_variant)
        selected_variant_info = FSR4_VARIANTS[selected_variant]
        selected_config_overrides = self._fsr4_variant_config_overrides(selected_variant)
        if previous_variant in VARIANT_RESET_OVERRIDES and selected_variant != previous_variant:
            for reset_key, reset_value in VARIANT_RESET_OVERRIDES[previous_variant].items():
                selected_config_overrides.setdefault(reset_key, reset_value)
        selected_upscaler_src = self._fsr4_variant_path(fgmod_path, selected_variant)
        if not selected_upscaler_src.exists():
            selected_upscaler_src = fgmod_path / FSR4_UPSCALER_FILENAME
        if not selected_upscaler_src.exists():
            return {
                "status": "error",
                "message": f"FSR4 upscaler variant not found for {selected_variant}. Reinstall OptiScaler.",
            }
        selected_extra_files = self._fsr4_variant_extra_files(selected_variant)
        optiscaler_version = self._fgmod_version(fgmod_path)
        selected_upscaler_sha256 = self._file_sha256(selected_upscaler_src)
        uses_variant_injector = bool(selected_variant_info.get("injector"))
        if not self._installed_injector_is_current(fgmod_path, selected_variant):
            return {
                "status": "error",
                "message": (
                    "The installed OptiScaler bundle is from an older plugin build and does not contain "
                    f"the current injector for {selected_variant_info['label']}. Press 'Update OptiScaler bundle' "
                    "at the top of the panel, then patch the game."
                ),
            }

        try:
            decky.logger.info(
                f"Manual patch started for {directory} with FSR4 variant {selected_variant} ({selected_variant_info['label']})"
            )

            managed_proxy_names = {dll_name}
            previous_dll_name = str(previous_marker_metadata.get("dll_name") or "").strip()
            if previous_dll_name:
                managed_proxy_names.add(previous_dll_name)
            # Evaluate before anything is deleted: the injector is removed by the cleanup loop.
            already_patched = self._has_plugin_injector(directory, fgmod_path)

            backed_up_proxies = self._backup_preexisting_proxy_files(
                directory, fgmod_path, managed_proxy_names if previous_marker_metadata else None
            )
            decky.logger.info(
                f"Backed up pre-existing proxy files: {backed_up_proxies}"
                if backed_up_proxies
                else "No pre-existing proxy files required backup"
            )

            removed_patch_files = []
            for filename in dict.fromkeys(PATCH_CLEANUP_FILES):
                path = directory / filename
                if not path.exists():
                    continue
                if filename in VARIANT_EXTRA_FILENAMES and not self._is_managed_support_file(path, fgmod_path):
                    # A driver DLL the user placed themselves: leave it for the
                    # backup loop below so it is restored on unpatch.
                    continue
                path.unlink()
                removed_patch_files.append(filename)
            decky.logger.info(
                f"Removed stale patch files: {removed_patch_files}"
                if removed_patch_files
                else "No stale patch files found to remove"
            )

            backed_up_originals = []
            removed_managed_support = []
            for dll in ORIGINAL_DLL_BACKUPS:
                source = directory / dll
                backup = directory / f"{dll}.b"
                if not source.exists() or backup.exists():
                    continue
                if (allow_managed_support_cleanup or already_patched) and self._is_managed_support_file(source, fgmod_path):
                    source.unlink()
                    removed_managed_support.append(dll)
                    continue
                shutil.move(source, backup)
                backed_up_originals.append(dll)
            if removed_managed_support:
                decky.logger.info(f"Removed managed support files before repatch: {removed_managed_support}")
            decky.logger.info(
                f"Backed up original game DLLs: {backed_up_originals}"
                if backed_up_originals
                else "No original game DLLs required backup"
            )

            # Builds up to 0.17 moved the game's d3dcompiler_47.dll aside without
            # ever replacing it. Put it back so the game keeps its own compiler.
            for legacy in LEGACY_BACKUP_FILES:
                legacy_backup = directory / f"{legacy}.b"
                legacy_original = directory / legacy
                if legacy_backup.exists() and not legacy_original.exists():
                    shutil.move(legacy_backup, legacy_original)
                    decky.logger.info(f"Restored {legacy} from a legacy backup")

            variant_renamed = self._fsr4_variant_renamed_proxy_path(fgmod_path, selected_variant, dll_name)
            variant_injector = self._fsr4_variant_injector_path(fgmod_path, selected_variant)
            root_renamed = fgmod_path / "renames" / dll_name
            destination_dll = directory / dll_name
            if variant_renamed and variant_renamed.exists():
                source_for_copy = variant_renamed
            elif variant_injector and variant_injector.exists():
                source_for_copy = variant_injector
            elif root_renamed.exists():
                source_for_copy = root_renamed
            else:
                source_for_copy = optiscaler_dll
            shutil.copy2(source_for_copy, destination_dll)
            decky.logger.info(f"Copied injector DLL from {source_for_copy} to {destination_dll}")

            target_ini = directory / "OptiScaler.ini"
            source_ini = fgmod_path / "OptiScaler.ini"
            if preserve_ini and target_ini.exists():
                decky.logger.info(f"Preserving existing OptiScaler.ini at {target_ini}")
            elif source_ini.exists():
                shutil.copy2(source_ini, target_ini)
                decky.logger.info(f"Copied OptiScaler.ini from {source_ini} to {target_ini}")
            else:
                decky.logger.warning("No OptiScaler.ini found to copy")

            if target_ini.exists():
                self._migrate_optiscaler_ini(target_ini)
                self._disable_hq_font_auto(target_ini)
                if not uses_variant_injector and self._needs_v10_fg_downgrade(target_ini):
                    decky.logger.info("Mapping v10 FG keys (FGInput=nvngxfg) back to the 0.9.4 vocabulary")
                    selected_config_overrides.setdefault("FrameGen.FGInput", "nukems")
                    selected_config_overrides.setdefault("FrameGen.FGOutput", "nukems")
                # FSR 4 watermark: a bundle-wide preference, applied on every (re)patch.
                watermark = bool(self._load_install_manifest(fgmod_path).get("fsr4_watermark"))
                current_watermark = (self._ini_current_value(target_ini, FSR4_WATERMARK_KEY) or "").lower()
                if watermark:
                    selected_config_overrides[FSR4_WATERMARK_KEY] = "true"
                elif current_watermark == "true":
                    selected_config_overrides[FSR4_WATERMARK_KEY] = "auto"
                previous_options = _normalize_game_options(previous_marker_metadata.get("game_options"))
                # Per-game frame generation choice.
                if game_options["frame_generation"] == "optifg":
                    selected_config_overrides.update(OPTIFG_OVERRIDES)
                elif previous_options["frame_generation"] == "optifg":
                    selected_config_overrides.update(OPTIFG_RESET)
                self._apply_optiscaler_ini_overrides(target_ini, selected_config_overrides)
                if previous_variant in FSR4_VARIANTS and previous_variant != selected_variant:
                    self._reset_optiscaler_ini_defaults(target_ini, FSR4_VARIANTS[previous_variant].get("config_defaults") or {})
                # Per-game upscaler choice: an explicit choice is written as a hard value;
                # going back to "auto" clears our own value so the runtime default applies.
                explicit_upscaler = _dx12_upscaler_ini_value(game_options["dx12_upscaler"], uses_variant_injector)
                if explicit_upscaler:
                    self._apply_optiscaler_ini_overrides(target_ini, {"Upscalers.Dx12Upscaler": explicit_upscaler})
                elif previous_options["dx12_upscaler"] != "auto":
                    self._apply_optiscaler_ini_overrides(target_ini, {"Upscalers.Dx12Upscaler": "auto"})
                self._apply_optiscaler_ini_defaults(target_ini, selected_variant_info.get("config_defaults") or {})

            plugins_src = fgmod_path / "plugins"
            plugins_dest = directory / "plugins"
            if plugins_src.exists():
                shutil.copytree(plugins_src, plugins_dest, dirs_exist_ok=True)
                decky.logger.info(f"Synced plugins directory from {plugins_src} to {plugins_dest}")
            else:
                decky.logger.warning("Plugins directory missing in fgmod bundle")

            d3d12_src = fgmod_path / "D3D12_Optiscaler"
            d3d12_dest = directory / "D3D12_Optiscaler"
            if d3d12_src.exists():
                shutil.copytree(d3d12_src, d3d12_dest, dirs_exist_ok=True)
                decky.logger.info(f"Copied D3D12_Optiscaler directory to {d3d12_dest}")
            else:
                decky.logger.warning("D3D12_Optiscaler directory missing in fgmod bundle")

            copied_support = []
            missing_support = []
            for filename in SUPPORT_FILES:
                source = fgmod_path / filename
                dest = directory / filename
                if source.exists():
                    shutil.copy2(source, dest)
                    copied_support.append(filename)
                else:
                    missing_support.append(filename)

            upscaler_dest = directory / FSR4_UPSCALER_FILENAME
            shutil.copy2(selected_upscaler_src, upscaler_dest)
            copied_support.append(FSR4_UPSCALER_FILENAME)

            for extra_file in selected_extra_files:
                source = self._fsr4_variant_extra_file_path(fgmod_path, selected_variant, extra_file["name"])
                dest = directory / extra_file["name"]
                if source.exists():
                    shutil.copy2(source, dest)
                    copied_support.append(extra_file["name"])
                else:
                    missing_support.append(extra_file["name"])

            if copied_support:
                decky.logger.info(f"Copied support files: {copied_support}")
            if missing_support:
                decky.logger.warning(f"Support files missing from fgmod bundle: {missing_support}")

            decky.logger.info(f"Manual patch complete for {directory}")
            return {
                "status": "success",
                "message": (
                    f"OptiScaler files copied to {directory} using "
                    f"{selected_variant_info['label']}"
                ),
                "fsr4_variant": selected_variant,
                "fsr4_variant_label": selected_variant_info["label"],
                "fsr4_upscaler_sha256": selected_upscaler_sha256,
                "game_options": game_options,
                # Known hashes of what was just copied, for the marker's file cache.
                "managed_file_hashes": {
                    dll_name: (
                        selected_variant_info["injector"]["sha256"]
                        if uses_variant_injector
                        else self._file_sha256(optiscaler_dll)
                    ),
                    FSR4_UPSCALER_FILENAME: selected_upscaler_sha256,
                    **{extra_file["name"]: extra_file["sha256"] for extra_file in selected_extra_files},
                },
                "optiscaler_version": optiscaler_version,
            }

        except PermissionError as exc:
            decky.logger.error(f"Manual patch permission error: {exc}")
            return {
                "status": "error",
                "message": f"Permission error while patching: {exc}",
            }
        except Exception as exc:
            decky.logger.error(f"Manual patch failed: {exc}")
            return {
                "status": "error",
                "message": f"Manual patch failed: {exc}",
            }

    def _manual_unpatch_directory_impl(self, directory: Path) -> dict:
        try:
            decky.logger.info(f"Manual unpatch started for {directory}")

            removed_files = []
            for filename in set(INJECTOR_FILENAMES + SUPPORT_FILES + VARIANT_EXTRA_FILENAMES + [FSR4_UPSCALER_FILENAME]):
                path = directory / filename
                if path.exists():
                    path.unlink()
                    removed_files.append(filename)
            decky.logger.info(f"Removed injector/support files: {removed_files}" if removed_files else "No injector/support files found to remove")

            legacy_removed = []
            for legacy in LEGACY_FILES:
                path = directory / legacy
                if path.exists():
                    try:
                        path.unlink()
                    except IsADirectoryError:
                        shutil.rmtree(path, ignore_errors=True)
                    legacy_removed.append(legacy)
            decky.logger.info(f"Removed legacy artifacts: {legacy_removed}" if legacy_removed else "No legacy artifacts present")

            # Only remove the ASI plugin(s) the bundle contributes; games and users keep
            # their own files in plugins/ (Cyber Engine Tweaks, other ASI mods).
            plugins_dir = directory / "plugins"
            if plugins_dir.is_dir():
                bundled_plugins = {"OptiPatcher.asi"}
                fgmod_plugins = Path(decky.HOME) / "fgmod" / "plugins"
                if fgmod_plugins.is_dir():
                    bundled_plugins.update(p.name for p in fgmod_plugins.iterdir() if p.is_file())
                for plugin_name in sorted(bundled_plugins):
                    plugin_file = plugins_dir / plugin_name
                    if plugin_file.is_file():
                        plugin_file.unlink()
                        decky.logger.info(f"Removed {plugin_file}")
                try:
                    plugins_dir.rmdir()
                    decky.logger.info(f"Removed empty plugins directory at {plugins_dir}")
                except OSError:
                    decky.logger.info(f"Kept non-empty plugins directory at {plugins_dir} (third-party files present)")

            d3d12_dir = directory / "D3D12_Optiscaler"
            if d3d12_dir.exists():
                shutil.rmtree(d3d12_dir, ignore_errors=True)
                decky.logger.info(f"Removed D3D12_Optiscaler directory from {d3d12_dir}")

            restored_backups = []
            for dll in dict.fromkeys(RESTORABLE_BACKUP_FILES):
                backup = directory / f"{dll}.b"
                original = directory / dll
                if backup.exists():
                    if original.exists():
                        original.unlink()
                    shutil.move(backup, original)
                    restored_backups.append(dll)
            decky.logger.info(f"Restored backups: {restored_backups}" if restored_backups else "No backups found to restore")

            uninstaller = directory / "fgmod-uninstaller.sh"
            if uninstaller.exists():
                uninstaller.unlink()
                decky.logger.info(f"Removed fgmod uninstaller at {uninstaller}")

            # The FRAMEGEN_PATCH marker is deliberately left alone here: it holds the
            # user's original Steam launch options, which unpatch_game hands back to
            # Steam before removing the marker itself. An Advanced-Mode unpatch has
            # no app id, so it must keep the marker for a later patch/unpatch.

            decky.logger.info(f"Manual unpatch complete for {directory}")
            return {
                "status": "success",
                "message": f"OptiScaler files removed from {directory}",
            }

        except PermissionError as exc:
            decky.logger.error(f"Manual unpatch permission error: {exc}")
            return {
                "status": "error",
                "message": f"Permission error while unpatching: {exc}",
            }
        except Exception as exc:
            decky.logger.error(f"Manual unpatch failed: {exc}")
            return {
                "status": "error",
                "message": f"Manual unpatch failed: {exc}",
            }

    # ── Steam library discovery ───────────────────────────────────────────────

    def _home_path(self) -> Path:
        try:
            return Path(decky.HOME)
        except TypeError:
            return Path(str(decky.HOME))

    def _steam_root_candidates(self) -> list[Path]:
        home = self._home_path()
        candidates = [
            home / ".local" / "share" / "Steam",
            home / ".steam" / "steam",
            home / ".steam" / "root",
            home / ".var" / "app" / "com.valvesoftware.Steam" / "home" / ".local" / "share" / "Steam",
            home / ".var" / "app" / "com.valvesoftware.Steam" / "home" / ".steam" / "steam",
        ]
        unique: list[Path] = []
        seen: set[str] = set()
        for c in candidates:
            key = str(c)
            if key not in seen:
                unique.append(c)
                seen.add(key)
        return unique

    def _steam_library_paths(self) -> list[Path]:
        """Steam roots plus every library in libraryfolders.vdf.

        Deduplicated by the *resolved* path (on SteamOS ~/.steam/steam and
        ~/.steam/root are symlinks to ~/.local/share/Steam) but the path is kept in
        the spelling Steam uses, because markers and running-process paths are
        matched against that spelling.
        """
        library_paths: list[Path] = []
        seen: set[str] = set()

        def add(candidate: Path) -> None:
            try:
                key = str(candidate.resolve())
            except OSError:
                key = str(candidate)
            if key not in seen:
                library_paths.append(candidate)
                seen.add(key)

        for steam_root in self._steam_root_candidates():
            if steam_root.exists():
                add(steam_root)
            library_file = steam_root / "steamapps" / "libraryfolders.vdf"
            if not library_file.exists():
                continue
            try:
                with open(library_file, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if '"path"' not in line:
                            continue
                        path = line.split('"path"', 1)[1].strip().strip('"').replace("\\\\", "/")
                        add(Path(path))
            except Exception as exc:
                decky.logger.error(f"[Framegen] failed to parse libraryfolders: {library_file}: {exc}")
        return library_paths

    def _find_installed_games(self, appid: str | None = None) -> list[dict]:
        games: list[dict] = []
        for library_path in self._steam_library_paths():
            steamapps_path = library_path / "steamapps"
            if not steamapps_path.exists():
                continue
            for appmanifest in steamapps_path.glob("appmanifest_*.acf"):
                game_info: dict = {"appid": "", "name": "", "library_path": str(library_path), "install_path": ""}
                install_dir = ""
                try:
                    with open(appmanifest, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            if '"appid"' in line:
                                game_info["appid"] = line.split('"appid"', 1)[1].strip().strip('"')
                            elif '"name"' in line:
                                game_info["name"] = line.split('"name"', 1)[1].strip().strip('"')
                            elif '"installdir"' in line:
                                install_dir = line.split('"installdir"', 1)[1].strip().strip('"')
                except Exception as exc:
                    decky.logger.error(f"[Framegen] skipping manifest {appmanifest}: {exc}")
                    continue
                if not game_info["appid"] or not game_info["name"]:
                    continue
                if "Proton" in game_info["name"] or "Steam Linux Runtime" in game_info["name"]:
                    continue
                install_path = steamapps_path / "common" / install_dir if install_dir else Path()
                game_info["install_path"] = str(install_path)
                if appid is None or str(game_info["appid"]) == str(appid):
                    games.append(game_info)
        deduped: dict[str, dict] = {}
        for game in games:
            deduped[str(game["appid"])] = game
        return sorted(deduped.values(), key=lambda g: g["name"].lower())

    def _game_record(self, appid: str) -> dict | None:
        matches = self._find_installed_games(appid)
        return matches[0] if matches else None

    # ── Patch target auto-detection ───────────────────────────────────────────

    def _normalized_path_string(self, value: str) -> str:
        normalized = value.lower().replace("\\", "/")
        normalized = normalized.replace("z:/", "/")
        normalized = normalized.replace("//", "/")
        return normalized

    def _candidate_executables(self, install_root: Path) -> list[Path]:
        if not install_root.exists():
            return []
        candidates: list[Path] = []
        try:
            for exe in install_root.rglob("*.exe"):
                if exe.is_file():
                    candidates.append(exe)
        except Exception as exc:
            decky.logger.error(f"[Framegen] exe scan failed for {install_root}: {exc}")
        return candidates

    def _exe_score(self, exe: Path, install_root: Path, game_name: str) -> int:
        normalized = self._normalized_path_string(str(exe))
        name = exe.name.lower()
        score = 0
        if normalized.endswith("-win64-shipping.exe"):
            score += 300
        if "shipping.exe" in name:
            score += 220
        if "/binaries/win64/" in normalized:
            score += 200
        if "/win64/" in normalized:
            score += 80
        if exe.parent == install_root:
            score += 20
        sanitized_game = re.sub(r"[^a-z0-9]", "", game_name.lower())
        sanitized_name = re.sub(r"[^a-z0-9]", "", exe.stem.lower())
        sanitized_root = re.sub(r"[^a-z0-9]", "", install_root.name.lower())
        if sanitized_game and sanitized_game in sanitized_name:
            score += 120
        if sanitized_root and sanitized_root in sanitized_name:
            score += 90
        for bad in BAD_EXE_SUBSTRINGS:
            if bad in normalized:
                score -= 200
        score -= len(exe.parts)
        return score

    def _best_running_executable(self, candidates: list[Path]) -> Path | None:
        if not candidates:
            return None
        try:
            result = subprocess.run(
                ["ps", "-eo", "args="],
                capture_output=True,
                text=True,
                check=False,
                env=self._host_env(),
            )
            if result.returncode != 0:
                decky.logger.warning(f"[Framegen] ps exited {result.returncode}: {result.stderr.strip()}")
            process_lines = result.stdout.splitlines()
        except Exception as exc:
            decky.logger.error(f"[Framegen] running exe scan failed: {exc}")
            return None
        # Match both the library's spelling and the resolved one: Steam launches the
        # game through the real path even when the library was found via a symlink.
        normalized_candidates: list[tuple[Path, str]] = []
        for exe in candidates:
            spellings = {str(exe)}
            try:
                spellings.add(str(exe.resolve()))
            except OSError:
                pass
            for spelling in spellings:
                normalized_candidates.append((exe, self._normalized_path_string(spelling)))
        matches: list[tuple[int, Path]] = []
        for line in process_lines:
            normalized_line = self._normalized_path_string(line)
            for exe, normalized_exe in normalized_candidates:
                if normalized_exe in normalized_line:
                    matches.append((len(normalized_exe), exe))
        if not matches:
            return None
        matches.sort(key=lambda item: item[0], reverse=True)
        return matches[0][1]

    def _guess_patch_target(self, game_info: dict) -> tuple[Path, Path | None]:
        install_root = Path(game_info["install_path"])
        candidates = self._candidate_executables(install_root)
        if not candidates:
            return install_root, None
        running_exe = self._best_running_executable(candidates)
        if running_exe:
            return running_exe.parent, running_exe
        best = max(candidates, key=lambda exe: self._exe_score(exe, install_root, game_info["name"]))
        return best.parent, best

    def _is_game_running(self, game_info: dict) -> bool:
        install_root = Path(game_info["install_path"])
        candidates = self._candidate_executables(install_root)
        return self._best_running_executable(candidates) is not None

    # ── Marker file tracking ──────────────────────────────────────────────────

    def _find_marker(self, install_root: Path) -> Path | None:
        if not install_root.exists():
            return None
        try:
            for marker in install_root.rglob(MARKER_FILENAME):
                if marker.is_file():
                    return marker
        except Exception:
            pass
        return None

    def _read_marker(self, marker_path: Path) -> dict:
        try:
            with open(marker_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _marker_target_dir(self, marker: Path, metadata: dict) -> Path:
        """patch_game always writes the marker into the patched directory, so the
        marker's own location is authoritative. The stored absolute path is kept
        only when it is the same directory under another spelling (a symlinked
        library), never when it points somewhere else (moved/copied install)."""
        stored = str(metadata.get("target_dir") or "").strip()
        if stored:
            stored_path = Path(stored)
            try:
                if stored_path.is_dir() and stored_path.resolve() == marker.parent.resolve():
                    return stored_path
            except OSError:
                pass
            decky.logger.info(f"[Framegen] marker target_dir {stored} is not the marker's directory; using {marker.parent}")
        return marker.parent

    def _write_marker(
        self,
        marker_path: Path,
        *,
        appid: str,
        game_name: str,
        dll_name: str,
        target_dir: Path,
        original_launch_options: str,
        backed_up_files: list[str],
        optiscaler_version: str | None = None,
        fsr4_variant: str | None = None,
        fsr4_upscaler_sha256: str | None = None,
        file_hashes: dict[str, str] | None = None,
        game_options: dict | None = None,
    ) -> None:
        normalized_variant = self._normalize_fsr4_variant(fsr4_variant)
        variant_info = FSR4_VARIANTS[normalized_variant]
        # sha256 + size + mtime of the big managed files, so status refreshes do not
        # re-hash ~200 MB every time. Invalidated by _cached_sha256 when a file changes.
        file_cache: dict[str, dict] = {}
        for name, sha in (file_hashes or {}).items():
            file_path = target_dir / name
            try:
                stat = file_path.stat()
            except OSError:
                continue
            if sha:
                file_cache[name] = {"sha256": sha.lower(), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        payload = {
            "file_cache": file_cache,
            "game_options": _normalize_game_options(game_options),
            "appid": str(appid),
            "game_name": game_name,
            "dll_name": dll_name,
            "target_dir": str(target_dir),
            "original_launch_options": original_launch_options,
            "backed_up_files": backed_up_files,
            "optiscaler_version": optiscaler_version,
            "fsr4_variant": normalized_variant,
            "fsr4_variant_label": variant_info["label"],
            "fsr4_upscaler_sha256": fsr4_upscaler_sha256,
            "managed_files": [
                {
                    "path": str(target_dir / FSR4_UPSCALER_FILENAME),
                    "sha256": fsr4_upscaler_sha256,
                    "kind": "fsr4-upscaler",
                    "variant": normalized_variant,
                }
            ],
            "patched_at": datetime.now(timezone.utc).isoformat(),
        }
        self._write_json_file(marker_path, payload)

    def _cached_sha256(self, path: Path, cache: dict | None) -> str:
        """sha256 of ``path`` from the marker's file cache when size and mtime still
        match, otherwise a fresh hash."""
        entry = (cache or {}).get(path.name) if isinstance(cache, dict) else None
        if isinstance(entry, dict):
            try:
                stat = path.stat()
                if stat.st_size == entry.get("size") and stat.st_mtime_ns == entry.get("mtime_ns") and entry.get("sha256"):
                    return str(entry["sha256"]).lower()
            except OSError:
                pass
        return self._file_sha256(path).lower()

    # ── Launch options helpers ────────────────────────────────────────────────

    def _build_managed_launch_options(self, dll_name: str) -> str:
        if dll_name == "OptiScaler.asi":
            return "SteamDeck=0 %command%"
        base = dll_name.replace(".dll", "")
        return f"WINEDLLOVERRIDES={base}=n,b SteamDeck=0 %command%"

    def _is_managed_launch_options(self, opts: str, managed_dll_name: str | None = None) -> bool:
        """True if ``opts`` is a launch string this plugin wrote (so it must not be
        stored as the user's own options). ``managed_dll_name`` is the proxy name
        recorded in an existing marker; the bare ``SteamDeck=0 %command%`` form is
        only claimed when a marker proves we wrote it, because a user could have
        typed exactly that themselves."""
        if not opts or not opts.strip():
            return False
        normalized = " ".join(opts.strip().split())
        unquoted = " ".join(normalized.replace('"', "").replace("'", "").split())
        for dll_name in VALID_DLL_NAMES:
            if dll_name == "OptiScaler.asi":
                continue
            if unquoted == self._build_managed_launch_options(dll_name):
                return True
        if managed_dll_name == "OptiScaler.asi" and unquoted == self._build_managed_launch_options("OptiScaler.asi"):
            return True
        for dll_name in VALID_DLL_NAMES:
            if dll_name == "OptiScaler.asi":
                continue
            base = dll_name.replace(".dll", "")
            if f"WINEDLLOVERRIDES={base}=n,b" in normalized:
                return True
        if "fgmod/fgmod" in normalized:
            return True
        return False

    def _looks_patched(self, directory: Path, fgmod_path: Path) -> bool:
        """Any evidence that this plugin (or a manual OptiScaler install) touched the folder."""
        if self._has_patch_fingerprint(directory):
            return True
        if any((directory / f"{name}.b").exists() for name in dict.fromkeys(RESTORABLE_BACKUP_FILES)):
            return True
        for name in PROXY_DLL_BACKUPS:
            candidate = directory / name
            if candidate.exists() and self._is_bundled_proxy_copy(candidate, fgmod_path):
                return True
        return False

    async def list_installed_games(self) -> dict:
        try:
            games = []
            for game in self._find_installed_games():
                install_root = Path(game["install_path"])
                games.append({
                    "appid": str(game["appid"]),
                    "name": game["name"],
                    "install_found": install_root.exists(),
                })
            return {"status": "success", "games": games}
        except Exception as e:
            decky.logger.error(str(e))
            return {"status": "error", "message": str(e)}

    async def get_path_defaults(self) -> dict:
        try:
            home_path = Path(decky.HOME)
        except TypeError:
            home_path = Path(str(decky.HOME))

        steam_common = home_path / ".local" / "share" / "Steam" / "steamapps" / "common"

        return {
            "home": str(home_path),
            "steam_common": str(steam_common),
        }

    async def log_error(self, error: str) -> None:
        decky.logger.error(f"FRONTEND: {error}")

    async def manual_patch_directory(
        self,
        directory: str,
        dll_name: str = "dxgi.dll",
        fsr4_variant: str = DEFAULT_FSR4_VARIANT,
    ) -> dict:
        if dll_name not in VALID_DLL_NAMES:
            return {"status": "error", "message": f"Invalid proxy DLL name: {dll_name}"}
        try:
            target_dir = self._resolve_target_directory(directory)
        except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
            decky.logger.error(f"Manual patch validation failed: {exc}")
            return {"status": "error", "message": str(exc)}

        allow_managed_support_cleanup = (target_dir / MARKER_FILENAME).exists()
        return self._manual_patch_directory_impl(
            target_dir,
            dll_name,
            fsr4_variant,
            allow_managed_support_cleanup=allow_managed_support_cleanup,
        )

    async def manual_unpatch_directory(self, directory: str) -> dict:
        try:
            target_dir = self._resolve_target_directory(directory)
        except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
            decky.logger.error(f"Manual unpatch validation failed: {exc}")
            return {"status": "error", "message": str(exc)}

        # The unpatch deletes a fixed list of DLL names. On a folder that was never
        # patched that would remove files the game itself ships (libxess.dll,
        # dbghelp.dll, plugins/ ...), so refuse unless there is evidence of a patch.
        if not self._looks_patched(target_dir, Path(decky.HOME) / "fgmod"):
            decky.logger.warning(f"Manual unpatch refused: no Framegen/OptiScaler patch found in {target_dir}")
            return {
                "status": "error",
                "message": "No Framegen/OptiScaler patch found in this directory. Nothing was changed.",
            }

        return self._manual_unpatch_directory_impl(target_dir)

    # ── AppID-based patch / unpatch / status ───────────────────────────────────────

    async def get_game_status(self, appid: str) -> dict:
        try:
            game_info = self._game_record(str(appid))
            if not game_info:
                return {
                    "status": "success",
                    "appid": str(appid),
                    "install_found": False,
                    "patched": False,
                    "dll_name": None,
                    "target_dir": None,
                    "fsr4_variant": None,
                    "fsr4_variant_label": None,
                    "message": "Game not found in Steam library.",
                }
            install_root = Path(game_info["install_path"])
            if not install_root.exists():
                return {
                    "status": "success",
                    "appid": str(appid),
                    "name": game_info["name"],
                    "install_found": False,
                    "patched": False,
                    "dll_name": None,
                    "target_dir": None,
                    "fsr4_variant": None,
                    "fsr4_variant_label": None,
                    "message": "Game install directory not found.",
                }
            marker = self._find_marker(install_root)
            if not marker:
                return {
                    "status": "success",
                    "appid": str(appid),
                    "name": game_info["name"],
                    "install_found": True,
                    "patched": False,
                    "dll_name": None,
                    "target_dir": None,
                    "fsr4_variant": None,
                    "fsr4_variant_label": None,
                    "message": "Not patched.",
                }
            metadata = self._read_marker(marker)
            dll_name = metadata.get("dll_name", "dxgi.dll")
            target_dir = self._marker_target_dir(marker, metadata)
            dll_present = (target_dir / dll_name).exists()
            file_cache = metadata.get("file_cache")
            upscaler_path = target_dir / FSR4_UPSCALER_FILENAME
            upscaler_sha256 = self._cached_sha256(upscaler_path, file_cache) if upscaler_path.exists() else None
            stored_variant = str(metadata.get("fsr4_variant") or "").strip() or None
            detected_variant = self._detect_fsr4_variant(
                target_dir, upscaler_sha256, target_dir / dll_name, stored_variant, file_cache
            )
            effective_variant = detected_variant or (stored_variant if stored_variant in FSR4_VARIANTS else None)
            effective_label = FSR4_VARIANTS[effective_variant]["label"] if effective_variant else None
            # A game patched by an older plugin build still carries that build's
            # injector under the proxy name; only a Reinstall replaces it.
            injector_outdated = False
            expected_injector = self._fsr4_variant_injector_info(effective_variant) if effective_variant else None
            if dll_present and expected_injector:
                try:
                    injector_outdated = (
                        self._cached_sha256(target_dir / dll_name, file_cache) != expected_injector["sha256"].lower()
                    )
                except Exception as exc:
                    decky.logger.warning(f"[Framegen] could not hash {target_dir / dll_name}: {exc}")
            if dll_present:
                message = f"Patched using {dll_name}" + (f" with {effective_label}." if effective_label else ".")
                if injector_outdated:
                    message += " The injector is from an older plugin build: press Reinstall."
            else:
                message = f"Marker found but {dll_name} is missing. Reinstall recommended."
            return {
                "status": "success",
                "appid": str(appid),
                "name": game_info["name"],
                "install_found": True,
                "patched": dll_present,
                "dll_name": dll_name,
                "target_dir": str(target_dir),
                "patched_at": metadata.get("patched_at"),
                "optiscaler_version": metadata.get("optiscaler_version"),
                "fsr4_variant": effective_variant,
                "fsr4_variant_label": effective_label,
                "fsr4_upscaler_sha256": upscaler_sha256,
                "injector_outdated": injector_outdated,
                "game_options": _normalize_game_options(metadata.get("game_options")),
                "ini_dx12_upscaler": self._ini_current_value(target_dir / "OptiScaler.ini", "Upscalers.Dx12Upscaler"),
                "ini_fg_input": self._ini_current_value(target_dir / "OptiScaler.ini", "FrameGen.FGInput"),
                "message": message,
            }
        except Exception as exc:
            decky.logger.error(f"[Framegen] get_game_status failed for {appid}: {exc}")
            return {"status": "error", "message": str(exc)}

    async def get_game_diagnostics(self, appid: str) -> dict:
        """Everything needed to debug one game in a single text: bundle state, marker,
        the INI keys the plugin manages and the telling lines of OptiScaler.log."""
        try:
            fgmod_path = Path(decky.HOME) / "fgmod"
            manifest = self._load_install_manifest(fgmod_path)
            plugin_version = "unknown"
            try:
                plugin_version = json.loads((Path(decky.DECKY_PLUGIN_DIR) / "package.json").read_text(encoding="utf-8")).get("version", "unknown")
            except Exception:
                pass
            lines = [
                f"Decky Framegen {plugin_version} diagnostics ({datetime.now(timezone.utc).isoformat()})",
                f"bundle: version={manifest.get('optiscaler', {}).get('version')} default_variant={manifest.get('selected_default_variant')} "
                f"fingerprint_current={str(manifest.get('bundle_fingerprint')) == BUNDLE_FINGERPRINT} watermark={bool(manifest.get('fsr4_watermark'))}",
            ]
            status = await self.get_game_status(str(appid))
            lines.append(f"game: appid={appid} name={status.get('name')} patched={status.get('patched')} dll={status.get('dll_name')} "
                         f"variant={status.get('fsr4_variant')} injector_outdated={status.get('injector_outdated')} target={status.get('target_dir')}")
            lines.append(f"options: {status.get('game_options')}")
            target_dir = Path(status["target_dir"]) if status.get("target_dir") else None
            if target_dir and target_dir.is_dir():
                ini = target_dir / "OptiScaler.ini"
                if ini.exists():
                    keys = ["Upscalers.Dx12Upscaler", "FrameGen.Enabled", "FrameGen.FGInput", "FrameGen.FGOutput", "FrameGen.FGNvngxReplacement",
                            "FSR.Fsr4Update", "FSR.Fsr4ForceEnableInt8", "FSR.Fsr4ForceModel", "FSR.Fsr4EnableWatermark",
                            "Plugins.LoadCustomAmdxc64OnRdna2", "Plugins.LoadAsiPlugins", "Menu.UseHQFont", "Menu.ShortcutKey"]
                    lines.append("ini: " + " ".join(f"{k.split('.')[1]}={self._ini_current_value(ini, k)}" for k in keys))
                present = [n for n in ["dxgi.dll", "winmm.dll", "version.dll", "OptiScaler.ini", "amdxcffx64.dll", "amdxc64.dll",
                                       FSR4_UPSCALER_FILENAME, "fakenvapi.dll", "plugins/OptiPatcher.asi", "D3D12_Optiscaler/D3D12Core.dll"]
                           if (target_dir / n).exists()]
                lines.append("files: " + ", ".join(present))
                log = target_dir / "OptiScaler.log"
                if log.exists():
                    try:
                        text = log.read_text(encoding="utf-8", errors="replace").splitlines()
                    except Exception as exc:
                        text = [f"<could not read OptiScaler.log: {exc}>"]
                    wanted = re.compile(r"OptiScaler v|Setting DllPath|Detected GPU|vkd3d|fsr4|FSR4|amdxc64|amdxcffx64|OptiInput|Fsr4|Upscaler support|LoadAsiPlugins|\bERROR\b|\bWARN\b", re.IGNORECASE)
                    picked = [l for l in text if wanted.search(l)][-60:]
                    lines.append(f"OptiScaler.log: {len(text)} lines, last modified {datetime.fromtimestamp(log.stat().st_mtime, tz=timezone.utc).isoformat()}")
                    lines.extend("  " + l for l in picked)
                    lines.append("  --- last 15 lines ---")
                    lines.extend("  " + l for l in text[-15:])
                else:
                    lines.append("OptiScaler.log: not found (launch the game once)")
            report = "\n".join(lines)
            try:
                fgmod_path.mkdir(exist_ok=True)
                (fgmod_path / f"diagnostics-{appid}.txt").write_text(report, encoding="utf-8")
            except Exception:
                pass
            return {"status": "success", "report": report, "path": str(fgmod_path / f"diagnostics-{appid}.txt")}
        except Exception as exc:
            decky.logger.error(f"[Framegen] get_game_diagnostics failed for {appid}: {exc}")
            return {"status": "error", "message": str(exc)}

    async def patch_game(
        self,
        appid: str,
        dll_name: str = "dxgi.dll",
        current_launch_options: str = "",
        fsr4_variant: str = DEFAULT_FSR4_VARIANT,
        dx12_upscaler: str = "auto",
        frame_generation: str = "default",
    ) -> dict:
        try:
            if dll_name not in VALID_DLL_NAMES:
                return {"status": "error", "message": f"Invalid proxy DLL name: {dll_name}"}
            game_options = _normalize_game_options({"dx12_upscaler": dx12_upscaler, "frame_generation": frame_generation})
            game_info = self._game_record(str(appid))
            if not game_info:
                return {"status": "error", "message": "Game not found in Steam library."}
            install_root = Path(game_info["install_path"])
            if not install_root.exists():
                return {"status": "error", "message": "Game install directory does not exist."}
            if self._is_game_running(game_info):
                return {"status": "error", "message": "Close the game before patching."}
            fgmod_path = Path(decky.HOME) / "fgmod"
            if not fgmod_path.exists():
                return {"status": "error", "message": "OptiScaler bundle not installed. Run Install first."}

            # Preserve true original launch options across re-patches
            original_launch_options = current_launch_options or ""
            existing_marker = self._find_marker(install_root)
            existing_marker_metadata = self._read_marker(existing_marker) if existing_marker else {}
            existing_marker_target_dir = (
                self._marker_target_dir(existing_marker, existing_marker_metadata) if existing_marker else None
            )
            managed_dll_name = str(existing_marker_metadata.get("dll_name") or "") if existing_marker else None
            if existing_marker:
                stored_opts = str(existing_marker_metadata.get("original_launch_options") or "")
                if stored_opts and not self._is_managed_launch_options(stored_opts, managed_dll_name):
                    original_launch_options = stored_opts
            if self._is_managed_launch_options(original_launch_options, managed_dll_name):
                original_launch_options = ""

            # Auto-detect the right directory to patch
            target_dir, target_exe = self._guess_patch_target(game_info)
            decky.logger.info(f"[Framegen] patch_game: appid={appid} dll={dll_name} target={target_dir} exe={target_exe}")

            allow_managed_support_cleanup = bool(
                existing_marker and existing_marker_target_dir == target_dir
            ) or (target_dir / MARKER_FILENAME).exists()
            result = self._manual_patch_directory_impl(
                target_dir,
                dll_name,
                fsr4_variant,
                allow_managed_support_cleanup=allow_managed_support_cleanup,
                game_options=game_options,
            )
            if result["status"] != "success":
                return result

            backed_up = [dll for dll in dict.fromkeys(RESTORABLE_BACKUP_FILES) if (target_dir / f"{dll}.b").exists()]
            marker_path = target_dir / MARKER_FILENAME
            self._write_marker(
                marker_path,
                appid=str(appid),
                game_name=game_info["name"],
                dll_name=dll_name,
                target_dir=target_dir,
                original_launch_options=original_launch_options,
                backed_up_files=backed_up,
                optiscaler_version=result.get("optiscaler_version"),
                fsr4_variant=result.get("fsr4_variant"),
                fsr4_upscaler_sha256=result.get("fsr4_upscaler_sha256"),
                file_hashes=result.get("managed_file_hashes"),
                game_options=game_options,
            )

            if existing_marker and existing_marker != marker_path:
                # The auto-detected target moved (a game update added a better
                # scoring exe). Clean the previous location so its OptiScaler files
                # and ".b" originals are not orphaned. The marker's own directory is
                # authoritative; the stored string may alias it through a symlink.
                old_dir = existing_marker.parent
                try:
                    same_dir = old_dir.resolve() == target_dir.resolve()
                except OSError:
                    same_dir = True
                if not same_dir and old_dir.is_dir():
                    decky.logger.info(f"[Framegen] patch target moved {old_dir} -> {target_dir}; cleaning previous location")
                    old_result = self._manual_unpatch_directory_impl(old_dir)
                    if old_result.get("status") != "success":
                        decky.logger.warning(f"[Framegen] failed to clean old patch location {old_dir}: {old_result.get('message')}")
                try:
                    existing_marker.unlink()
                except FileNotFoundError:
                    pass

            managed_launch_options = self._build_managed_launch_options(dll_name)
            decky.logger.info(f"[Framegen] patch_game success: appid={appid} launch_options={managed_launch_options}")
            return {
                "status": "success",
                "appid": str(appid),
                "name": game_info["name"],
                "dll_name": dll_name,
                "target_dir": str(target_dir),
                "launch_options": managed_launch_options,
                "original_launch_options": original_launch_options,
                "optiscaler_version": result.get("optiscaler_version"),
                "fsr4_variant": result.get("fsr4_variant"),
                "fsr4_variant_label": result.get("fsr4_variant_label"),
                "fsr4_upscaler_sha256": result.get("fsr4_upscaler_sha256"),
                "message": (
                    f"Patched {game_info['name']} using {dll_name} "
                    f"with {result.get('fsr4_variant_label', FSR4_VARIANTS[self._normalize_fsr4_variant(fsr4_variant)]['label'])}."
                ),
            }
        except Exception as exc:
            decky.logger.error(f"[Framegen] patch_game failed for {appid}: {exc}")
            return {"status": "error", "message": str(exc)}

    async def unpatch_game(self, appid: str) -> dict:
        try:
            game_info = self._game_record(str(appid))
            if not game_info:
                return {"status": "error", "message": "Game not found in Steam library."}
            install_root = Path(game_info["install_path"])
            if not install_root.exists():
                return {
                    "status": "success",
                    "appid": str(appid),
                    "name": game_info["name"],
                    "launch_options": "",
                    "message": "Game install directory does not exist.",
                }
            if self._is_game_running(game_info):
                return {"status": "error", "message": "Close the game before unpatching."}
            marker = self._find_marker(install_root)
            if not marker:
                return {
                    "status": "success",
                    "appid": str(appid),
                    "name": game_info["name"],
                    "launch_options": "",
                    "message": "No Framegen patch found for this game.",
                }
            metadata = self._read_marker(marker)
            target_dir = self._marker_target_dir(marker, metadata)
            original_launch_options = str(metadata.get("original_launch_options") or "")
            result = self._manual_unpatch_directory_impl(target_dir)
            if result.get("status") != "success":
                # Keep the marker so the game still shows as patched and can be retried.
                return result
            try:
                marker.unlink()
            except FileNotFoundError:
                pass
            decky.logger.info(f"[Framegen] unpatch_game success: appid={appid} target={target_dir}")
            return {
                "status": "success",
                "appid": str(appid),
                "name": game_info["name"],
                "launch_options": original_launch_options,
                "message": f"Unpatched {game_info['name']}.",
            }
        except Exception as exc:
            decky.logger.error(f"[Framegen] unpatch_game failed for {appid}: {exc}")
            return {"status": "error", "message": str(exc)}

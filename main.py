import decky
import os
import subprocess
import json
import shutil
import re
import filecmp
import hashlib
from datetime import datetime, timezone
from pathlib import Path

OPTISCALER_ARCHIVE_ASSET = {
    "name": "Optiscaler_0.9.2a-final.20260517._Reup.7z",
    "sha256": "6426a16085f6128c810e0de58947029664439afd0567b6a286c0e3ef784a92a1",
    "version": "0.9.2a-final.20260517._Reup",
}

FSR4_INT8_ASSET = {
    "name": "amd_fidelityfx_upscaler_dx12.dll",
    "sha256": "c7720bc16bede334f59a1a32cd22edbcbbb159685ed5240e61350a5fb0bc8a94",
    "version": "4.0.2c",
}

OPTIPATCHER_ASSET = {
    "name": "OptiPatcher_rolling.asi",
    "sha256": "88b9e1be3559737cd205fdf5f2c8550cf1923fb1def4c603e5bf03c3e84131b1",
    "version": "rolling",
}

FSR4_UPSCALER_FILENAME = "amd_fidelityfx_upscaler_dx12.dll"
INSTALL_MANIFEST_FILENAME = "install-manifest.json"
VERSION_FILENAME = "version.txt"
DEFAULT_FSR4_VARIANT = "rdna23-int8"

FSR4_VARIANTS = {
    "rdna23-int8": {
        "label": "Steam Deck / RDNA2-3 optimized",
        "dir_name": "fsr4-rdna2-3",
        "sha256": "c7720bc16bede334f59a1a32cd22edbcbbb159685ed5240e61350a5fb0bc8a94",
        "source_asset_name": FSR4_INT8_ASSET["name"],
        "source_version": FSR4_INT8_ASSET["version"],
        "uses_archive_native": False,
    },
    "rdna4-native": {
        "label": "Native bundle / RDNA4",
        "dir_name": "fsr4-rdna4",
        "sha256": "ec7ed3ca674e288240e6f04b986342aece47454c41d9b0959449e82e22bd7f6d",
        "source_asset_name": OPTISCALER_ARCHIVE_ASSET["name"],
        "source_version": OPTISCALER_ARCHIVE_ASSET["version"],
        "uses_archive_native": True,
    },
}
FSR4_VARIANT_BY_SHA256 = {
    variant["sha256"].lower(): variant_id
    for variant_id, variant in FSR4_VARIANTS.items()
    if variant.get("sha256")
}

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

ORIGINAL_DLL_BACKUPS = [
    "d3dcompiler_47.dll",
    "amd_fidelityfx_dx12.dll",
    "amd_fidelityfx_framegeneration_dx12.dll",
    FSR4_UPSCALER_FILENAME,
    "amd_fidelityfx_vk.dll",
]

RESTORABLE_BACKUP_FILES = [
    *PROXY_DLL_BACKUPS,
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
        try:
            return file_a.exists() and file_b.exists() and filecmp.cmp(file_a, file_b, shallow=False)
        except Exception:
            return False

    def _is_bundled_proxy_copy(self, file_path: Path, fgmod_path: Path) -> bool:
        bundled_copy = fgmod_path / "renames" / file_path.name
        return self._files_match(file_path, bundled_copy)

    def _has_patch_fingerprint(self, directory: Path) -> bool:
        return any((directory / filename).exists() for filename in PATCH_FINGERPRINT_FILES)

    def _backup_preexisting_proxy_files(self, directory: Path, fgmod_path: Path) -> list[str]:
        backed_up: list[str] = []
        already_patched = self._has_patch_fingerprint(directory)
        for filename in PROXY_DLL_BACKUPS:
            source = directory / filename
            backup = directory / f"{filename}.b"
            if not source.exists() or backup.exists():
                continue
            if already_patched or self._is_bundled_proxy_copy(source, fgmod_path):
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

    def _extract_archive(self, archive_path: Path, output_dir: Path, members: list[str] | None = None) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        extract_cmd = [
            "7z",
            "x",
            "-y",
            "-o" + str(output_dir),
            str(archive_path),
        ]
        if members:
            extract_cmd.extend(members)

        clean_env = os.environ.copy()
        clean_env["LD_LIBRARY_PATH"] = ""
        result = subprocess.run(
            extract_cmd,
            capture_output=True,
            text=True,
            check=False,
            env=clean_env,
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

    def _fsr4_variant_path(self, fgmod_path: Path, fsr4_variant: str | None) -> Path:
        variant_id = self._normalize_fsr4_variant(fsr4_variant)
        return fgmod_path / FSR4_VARIANTS[variant_id]["dir_name"] / FSR4_UPSCALER_FILENAME

    def _activate_default_fsr4_variant(self, fgmod_path: Path, fsr4_variant: str | None) -> str:
        variant_id = self._normalize_fsr4_variant(fsr4_variant)
        variant_path = self._fsr4_variant_path(fgmod_path, variant_id)
        if not variant_path.exists():
            raise FileNotFoundError(f"Prepared FSR4 variant missing: {variant_path}")
        shutil.copy2(variant_path, fgmod_path / FSR4_UPSCALER_FILENAME)
        return variant_id

    def _detect_fsr4_variant(self, upscaler_sha256: str | None) -> str | None:
        if not upscaler_sha256:
            return None
        return FSR4_VARIANT_BY_SHA256.get(str(upscaler_sha256).lower())

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
                
                # Replace Path=auto with Path=plugins
                updated_content = re.sub(r'Path\s*=\s*auto', 'Path=plugins', updated_content)

                # Disable new HQ font auto mode to avoid missing font assertions on Proton
                updated_content = re.sub(r'UseHQFont\s*=\s*auto', 'UseHQFont=false', updated_content)
                
                with open(ini_file, 'w') as f:
                    f.write(updated_content)
                
                decky.logger.info("Modified OptiScaler.ini to set FGInput=nukems, FGOutput=nukems, Fsr4Update=true, LoadAsiPlugins=true, Path=plugins, UseHQFont=false")
                return True
            else:
                decky.logger.warning(f"OptiScaler.ini not found at {ini_file}")
                return False
        except Exception as e:
            decky.logger.error(f"Failed to modify OptiScaler.ini: {e}")
            return False

    async def extract_static_optiscaler(self, selected_default_variant: str = DEFAULT_FSR4_VARIANT) -> dict:
        """Prepare the shared ~/fgmod bundle with both FSR4 runtime variants."""
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
            optipatcher_src = bin_path / OPTIPATCHER_ASSET["name"]
            for required_path, asset in [
                (optiscaler_archive, OPTISCALER_ARCHIVE_ASSET),
                (fsr4_int8_src, FSR4_INT8_ASSET),
                (optipatcher_src, OPTIPATCHER_ASSET),
            ]:
                if not required_path.exists():
                    return {
                        "status": "error",
                        "message": f"Required bundled asset missing: {asset['name']}",
                    }
                self._verify_bundled_asset(required_path, asset["sha256"], asset["name"])

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
                    }
                    for variant_id, variant in FSR4_VARIANTS.items()
                },
                "selected_default_variant": selected_default_variant,
                "active_root_upscaler": {
                    "path": FSR4_UPSCALER_FILENAME,
                    "sha256": active_upscaler_sha256,
                    "variant": selected_default_variant,
                },
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

    async def run_install_fgmod(self, selected_default_variant: str = DEFAULT_FSR4_VARIANT) -> dict:
        try:
            decky.logger.info("Starting OptiScaler installation from static bundle")
            selected_default_variant = self._normalize_fsr4_variant(selected_default_variant)

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

    async def check_fgmod_path(self) -> dict:
        path = Path(decky.HOME) / "fgmod"
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

        if not path.exists():
            return {"exists": False}

        for file_name in required_files:
            if not path.joinpath(file_name).exists():
                return {"exists": False}

        plugins_dir = path / "plugins"
        if not plugins_dir.exists() or not (plugins_dir / "OptiPatcher.asi").exists():
            return {"exists": False}

        for variant in FSR4_VARIANTS.values():
            variant_path = path / variant["dir_name"] / FSR4_UPSCALER_FILENAME
            if not variant_path.exists():
                return {"exists": False}

        manifest = self._load_install_manifest(path)
        selected_variant = self._selected_fsr4_variant(path)
        return {
            "exists": True,
            "version": self._fgmod_version(path),
            "selected_fsr4_variant": selected_variant,
            "selected_fsr4_variant_label": FSR4_VARIANTS[selected_variant]["label"],
            "install_manifest_present": bool(manifest),
        }

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
    ) -> dict:
        fgmod_path = Path(decky.HOME) / "fgmod"
        if not fgmod_path.exists():
            return {
                "status": "error",
                "message": "OptiScaler bundle not installed. Run Install first.",
            }

        optiscaler_dll = fgmod_path / "OptiScaler.dll"
        if not optiscaler_dll.exists():
            return {
                "status": "error",
                "message": "OptiScaler.dll not found in ~/fgmod. Reinstall OptiScaler.",
            }

        preserve_ini = True
        selected_variant = self._selected_fsr4_variant(fgmod_path, fsr4_variant)
        selected_variant_info = FSR4_VARIANTS[selected_variant]
        selected_upscaler_src = self._fsr4_variant_path(fgmod_path, selected_variant)
        if not selected_upscaler_src.exists():
            selected_upscaler_src = fgmod_path / FSR4_UPSCALER_FILENAME
        if not selected_upscaler_src.exists():
            return {
                "status": "error",
                "message": f"FSR4 upscaler variant not found for {selected_variant}. Reinstall OptiScaler.",
            }
        optiscaler_version = self._fgmod_version(fgmod_path)
        selected_upscaler_sha256 = self._file_sha256(selected_upscaler_src)

        try:
            decky.logger.info(
                f"Manual patch started for {directory} with FSR4 variant {selected_variant} ({selected_variant_info['label']})"
            )

            backed_up_proxies = self._backup_preexisting_proxy_files(directory, fgmod_path)
            decky.logger.info(
                f"Backed up pre-existing proxy files: {backed_up_proxies}"
                if backed_up_proxies
                else "No pre-existing proxy files required backup"
            )

            removed_patch_files = []
            for filename in dict.fromkeys(PATCH_CLEANUP_FILES):
                path = directory / filename
                if path.exists():
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
                if allow_managed_support_cleanup and self._is_managed_support_file(source, fgmod_path):
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

            renamed = fgmod_path / "renames" / dll_name
            destination_dll = directory / dll_name
            source_for_copy = renamed if renamed.exists() else optiscaler_dll
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
            for filename in set(INJECTOR_FILENAMES + SUPPORT_FILES + [FSR4_UPSCALER_FILENAME]):
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

            plugins_dir = directory / "plugins"
            if plugins_dir.exists():
                shutil.rmtree(plugins_dir, ignore_errors=True)
                decky.logger.info(f"Removed plugins directory at {plugins_dir}")

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
        library_paths: list[Path] = []
        seen: set[str] = set()
        for steam_root in self._steam_root_candidates():
            if steam_root.exists():
                key = str(steam_root)
                if key not in seen:
                    library_paths.append(steam_root)
                    seen.add(key)
            library_file = steam_root / "steamapps" / "libraryfolders.vdf"
            if not library_file.exists():
                continue
            try:
                with open(library_file, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if '"path"' not in line:
                            continue
                        path = line.split('"path"', 1)[1].strip().strip('"').replace("\\\\", "/")
                        candidate = Path(path)
                        key = str(candidate)
                        if key not in seen:
                            library_paths.append(candidate)
                            seen.add(key)
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
            result = subprocess.run(["ps", "-eo", "args="], capture_output=True, text=True, check=False)
            process_lines = result.stdout.splitlines()
        except Exception as exc:
            decky.logger.error(f"[Framegen] running exe scan failed: {exc}")
            return None
        normalized_candidates = [(exe, self._normalized_path_string(str(exe))) for exe in candidates]
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
    ) -> None:
        normalized_variant = self._normalize_fsr4_variant(fsr4_variant)
        variant_info = FSR4_VARIANTS[normalized_variant]
        payload = {
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

    # ── Launch options helpers ────────────────────────────────────────────────

    def _build_managed_launch_options(self, dll_name: str) -> str:
        if dll_name == "OptiScaler.asi":
            return "SteamDeck=0 %command%"
        base = dll_name.replace(".dll", "")
        return f"WINEDLLOVERRIDES={base}=n,b SteamDeck=0 %command%"

    def _is_managed_launch_options(self, opts: str) -> bool:
        if not opts or not opts.strip():
            return False
        normalized = " ".join(opts.strip().split())
        for dll_name in VALID_DLL_NAMES:
            if dll_name == "OptiScaler.asi":
                continue
            base = dll_name.replace(".dll", "")
            if f"WINEDLLOVERRIDES={base}=n,b" in normalized:
                return True
        if "fgmod/fgmod" in normalized:
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
            target_dir = Path(metadata.get("target_dir", str(marker.parent)))
            dll_present = (target_dir / dll_name).exists()
            upscaler_path = target_dir / FSR4_UPSCALER_FILENAME
            upscaler_sha256 = self._file_sha256(upscaler_path) if upscaler_path.exists() else None
            detected_variant = self._detect_fsr4_variant(upscaler_sha256)
            stored_variant = str(metadata.get("fsr4_variant") or "").strip() or None
            effective_variant = detected_variant or (stored_variant if stored_variant in FSR4_VARIANTS else None)
            effective_label = FSR4_VARIANTS[effective_variant]["label"] if effective_variant else None
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
                "message": (
                    f"Patched using {dll_name}" + (f" with {effective_label}." if effective_label else ".")
                    if dll_present
                    else f"Marker found but {dll_name} is missing. Reinstall recommended."
                ),
            }
        except Exception as exc:
            decky.logger.error(f"[Framegen] get_game_status failed for {appid}: {exc}")
            return {"status": "error", "message": str(exc)}

    async def patch_game(
        self,
        appid: str,
        dll_name: str = "dxgi.dll",
        current_launch_options: str = "",
        fsr4_variant: str = DEFAULT_FSR4_VARIANT,
    ) -> dict:
        try:
            if dll_name not in VALID_DLL_NAMES:
                return {"status": "error", "message": f"Invalid proxy DLL name: {dll_name}"}
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
            existing_marker_target_dir = Path(
                existing_marker_metadata.get("target_dir", str(existing_marker.parent))
            ) if existing_marker else None
            if existing_marker:
                stored_opts = str(existing_marker_metadata.get("original_launch_options") or "")
                if stored_opts and not self._is_managed_launch_options(stored_opts):
                    original_launch_options = stored_opts
            if self._is_managed_launch_options(original_launch_options):
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
            )

            if existing_marker and existing_marker != marker_path:
                try:
                    existing_marker.unlink()
                except Exception:
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
            target_dir = Path(metadata.get("target_dir", str(marker.parent)))
            original_launch_options = str(metadata.get("original_launch_options") or "")
            self._manual_unpatch_directory_impl(target_dir)
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

import decky
import os
import subprocess
import json
import shutil
import re
from datetime import datetime, timezone
from pathlib import Path

# Toggle to enable overwriting the upscaler DLL from the static remote binary.
# Set to False or comment out this constant to skip the overwrite by default.
UPSCALER_OVERWRITE_ENABLED = True

VALID_DLL_NAMES = {
    "dxgi.dll",
    "winmm.dll",
    "dbghelp.dll",
    "version.dll",
    "wininet.dll",
    "winhttp.dll",
    "OptiScaler.asi",
}

INJECTOR_FILENAMES = [
    "dxgi.dll",
    "winmm.dll",
    "nvngx.dll",
    "_nvngx.dll",
    "nvngx-wrapper.dll",
    "dlss-enabler.dll",
    "OptiScaler.dll",
]

ORIGINAL_DLL_BACKUPS = [
    "d3dcompiler_47.dll",
    "amd_fidelityfx_dx12.dll",
    "amd_fidelityfx_framegeneration_dx12.dll",
    "amd_fidelityfx_upscaler_dx12.dll",
    "amd_fidelityfx_vk.dll",
]

SUPPORT_FILES = [
    "libxess.dll",
    "libxess_dx11.dll",
    "libxess_fg.dll",
    "libxell.dll",
    "amd_fidelityfx_dx12.dll",
    "amd_fidelityfx_framegeneration_dx12.dll",
    "amd_fidelityfx_upscaler_dx12.dll",
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

    async def extract_static_optiscaler(self) -> dict:
        """Extract OptiScaler from the plugin's bin directory and copy additional files."""
        try:
            decky.logger.info("Starting extract_static_optiscaler method")
            
            # Set up paths
            bin_path = Path(decky.DECKY_PLUGIN_DIR) / "bin"
            extract_path = Path(decky.HOME) / "fgmod"
            
            decky.logger.info(f"Bin path: {bin_path}")
            decky.logger.info(f"Extract path: {extract_path}")
            
            # Check if bin directory exists
            if not bin_path.exists():
                decky.logger.error(f"Bin directory does not exist: {bin_path}")
                return {"status": "error", "message": f"Bin directory not found: {bin_path}"}
            
            # List files in bin directory for debugging
            bin_files = list(bin_path.glob("*"))
            decky.logger.info(f"Files in bin directory: {[f.name for f in bin_files]}")
            
            # Find the OptiScaler archive in the bin directory
            optiscaler_archive = None
            for file in bin_path.glob("*.7z"):
                decky.logger.info(f"Checking 7z file: {file.name}")
                # Check for both "OptiScaler" and "Optiscaler" (case variations) and exclude BUNDLE files
                if ("OptiScaler" in file.name or "Optiscaler" in file.name) and "BUNDLE" not in file.name:
                    optiscaler_archive = file
                    decky.logger.info(f"Found OptiScaler archive: {file.name}")
                    break
            
            if not optiscaler_archive:
                decky.logger.error("OptiScaler archive not found in plugin bin directory")
                return {"status": "error", "message": "OptiScaler archive not found in plugin bin directory"}
            
            decky.logger.info(f"Using archive: {optiscaler_archive}")
            
            # Clean up existing directory
            if extract_path.exists():
                decky.logger.info(f"Removing existing directory: {extract_path}")
                shutil.rmtree(extract_path)
            
            extract_path.mkdir(exist_ok=True)
            decky.logger.info(f"Created extract directory: {extract_path}")
            
            decky.logger.info(f"Extracting {optiscaler_archive.name} to {extract_path}")
            
            # Extract the 7z file
            extract_cmd = [
                "7z",
                "x",
                "-y",
                "-o" + str(extract_path),
                str(optiscaler_archive)
            ]
            
            decky.logger.info(f"Running extraction command: {' '.join(extract_cmd)}")
            
            # Create a clean environment to avoid PyInstaller issues
            clean_env = os.environ.copy()
            clean_env["LD_LIBRARY_PATH"] = ""
            
            decky.logger.info("Starting subprocess.run for extraction")
            extract_result = subprocess.run(
                extract_cmd,
                capture_output=True,
                text=True,
                check=False,
                env=clean_env
            )
            
            decky.logger.info(f"Extraction completed with return code: {extract_result.returncode}")
            decky.logger.info(f"Extraction stdout: {extract_result.stdout}")
            if extract_result.stderr:
                decky.logger.info(f"Extraction stderr: {extract_result.stderr}")
            
            if extract_result.returncode != 0:
                decky.logger.error(f"Extraction failed: {extract_result.stderr}")
                return {
                    "status": "error",
                    "message": f"Failed to extract OptiScaler archive: {extract_result.stderr}"
                }
            
            # Copy additional individual files from bin directory
            # Note: v0.9.0-final includes dlssg_to_fsr3_amd_is_better.dll, fakenvapi.dll, and fakenvapi.ini in the 7z
            # Only copy files that aren't already in the archive (separate remote binaries)
            # nvngx.dll is intentionally excluded: it was a stale DLSS 3.10.3 stub from a
            # pre-0.9 nightly that is missing DLSS 3.1+ exports (AllocateParameters,
            # GetCapabilityParameters, Init_with_ProjectID, etc.) present in OptiScaler
            # 0.9.0-final's own NGX proxy layer.  OptiScaler handles all NGX interception
            # internally; the bare nvidia DLL caused export-not-found failures on Proton.
            additional_files = [
                "OptiPatcher_rolling.asi"  # ASI plugin for OptiScaler spoofing
            ]
            
            decky.logger.info("Starting additional files copy")
            for file_name in additional_files:
                src_file = bin_path / file_name
                dest_file = extract_path / file_name
                
                decky.logger.info(f"Checking for additional file: {file_name} at {src_file}")
                if src_file.exists():
                    shutil.copy2(src_file, dest_file)
                    decky.logger.info(f"Copied additional file: {file_name}")
                else:
                    decky.logger.warning(f"Additional file not found: {file_name}")
                    return {
                        "status": "error",
                        "message": f"Required file {file_name} not found in plugin bin directory"
                    }
            
            decky.logger.info("Creating renamed copies of OptiScaler.dll")
            # Create renamed copies of OptiScaler.dll
            source_file = extract_path / "OptiScaler.dll"
            renames_dir = extract_path / "renames"
            self._create_renamed_copies(source_file, renames_dir)
            
            decky.logger.info("Copying launcher scripts")
            # Copy launcher scripts from assets
            assets_dir = Path(decky.DECKY_PLUGIN_DIR) / "assets"
            self._copy_launcher_scripts(assets_dir, extract_path)

            decky.logger.info("Setting up ASI plugins directory")
            # Create plugins directory and copy OptiPatcher ASI file
            try:
                plugins_dir = extract_path / "plugins"
                plugins_dir.mkdir(exist_ok=True)
                decky.logger.info(f"Created plugins directory: {plugins_dir}")
                
                # Copy OptiPatcher ASI file to plugins directory
                asi_src = bin_path / "OptiPatcher_rolling.asi"
                asi_dst = plugins_dir / "OptiPatcher.asi"  # Rename to generic name
                
                if asi_src.exists():
                    shutil.copy2(asi_src, asi_dst)
                    decky.logger.info(f"Copied OptiPatcher ASI to plugins directory: {asi_dst}")
                else:
                    decky.logger.warning("OptiPatcher ASI file not found in bin directory")
            except Exception as e:
                decky.logger.error(f"Failed to setup ASI plugins directory: {e}")

            decky.logger.info("Starting upscaler DLL overwrite check")
            # Optionally overwrite amd_fidelityfx_upscaler_dx12.dll with the separately bundled
            # RDNA2-optimized static binary used for Steam Deck compatibility.
            # Toggle via env DECKY_SKIP_UPSCALER_OVERWRITE=true to skip.
            try:
                skip_overwrite = os.environ.get("DECKY_SKIP_UPSCALER_OVERWRITE", "false").lower() in ("1", "true", "yes")
                if UPSCALER_OVERWRITE_ENABLED and not skip_overwrite:
                    upscaler_src = bin_path / "amd_fidelityfx_upscaler_dx12.dll"
                    upscaler_dst = extract_path / "amd_fidelityfx_upscaler_dx12.dll"
                    if upscaler_src.exists():
                        shutil.copy2(upscaler_src, upscaler_dst)
                        decky.logger.info("Overwrote amd_fidelityfx_upscaler_dx12.dll with static remote binary")
                    else:
                        decky.logger.warning("amd_fidelityfx_upscaler_dx12.dll not found in bin; skipping overwrite")
                else:
                    decky.logger.info("Skipping upscaler DLL overwrite due to DECKY_SKIP_UPSCALER_OVERWRITE")
            except Exception as e:
                decky.logger.error(f"Failed upscaler overwrite step: {e}")
            
            # Extract version from filename (e.g., OptiScaler_0.7.9.7z -> v0.7.9)
            version_match = optiscaler_archive.name.replace('.7z', '')
            if 'OptiScaler_' in version_match:
                version = 'v' + version_match.split('OptiScaler_')[1]
            elif 'Optiscaler_' in version_match:
                version = 'v' + version_match.split('Optiscaler_')[1]
            else:
                version = version_match
            
            # Create version file
            version_file = extract_path / "version.txt"
            try:
                with open(version_file, 'w') as f:
                    f.write(version)
                decky.logger.info(f"Created version file: {version}")
            except Exception as e:
                decky.logger.error(f"Failed to create version file: {e}")
            
            # Modify OptiScaler.ini to set FGType=nukems and Fsr4Update=true
            decky.logger.info("Modifying OptiScaler.ini")
            ini_file = extract_path / "OptiScaler.ini"
            self._modify_optiscaler_ini(ini_file)
            
            decky.logger.info(f"Successfully completed extraction to ~/fgmod with version {version}")
            return {
                "status": "success",
                "message": f"Successfully extracted OptiScaler {version} to ~/fgmod",
                "version": version
            }
            
        except Exception as e:
            decky.logger.error(f"Extract failed with exception: {str(e)}")
            decky.logger.error(f"Exception type: {type(e).__name__}")
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

    async def run_install_fgmod(self) -> dict:
        try:
            decky.logger.info("Starting OptiScaler installation from static bundle")
            
            # Extract the static OptiScaler bundle
            extract_result = await self.extract_static_optiscaler()
            
            if extract_result["status"] != "success":
                return {
                    "status": "error",
                    "message": f"OptiScaler extraction failed: {extract_result.get('message', 'Unknown error')}"
                }
            
            return {
                "status": "success",
                "output": "Successfully installed OptiScaler with all necessary components! You can now replace DLSS with FSR Frame Gen!"
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
            "fakenvapi.dll",        # v0.9.0-final includes fakenvapi.dll in archive
            "fakenvapi.ini",
            "amd_fidelityfx_dx12.dll",
            "amd_fidelityfx_framegeneration_dx12.dll",
            "amd_fidelityfx_upscaler_dx12.dll",
            "amd_fidelityfx_vk.dll", 
            "libxess.dll",
            "libxess_dx11.dll",
            "libxess_fg.dll",       # added in v0.9.0
            "libxell.dll",          # added in v0.9.0
            "fgmod",
            "fgmod-uninstaller.sh",
            "update-optiscaler-config.py"
        ]

        if path.exists():
            # Check required files
            for file_name in required_files:
                if not path.joinpath(file_name).exists():
                    return {"exists": False}

            # Check plugins directory and OptiPatcher ASI
            plugins_dir = path / "plugins"
            if not plugins_dir.exists() or not (plugins_dir / "OptiPatcher.asi").exists():
                return {"exists": False}

            return {"exists": True}
        else:
            return {"exists": False}

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

    def _manual_patch_directory_impl(self, directory: Path, dll_name: str = "dxgi.dll") -> dict:
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

        try:
            decky.logger.info(f"Manual patch started for {directory}")

            removed_injectors = []
            for filename in INJECTOR_FILENAMES:
                path = directory / filename
                if path.exists():
                    path.unlink()
                    removed_injectors.append(filename)
            decky.logger.info(f"Removed injector DLLs: {removed_injectors}" if removed_injectors else "No injector DLLs found to remove")

            backed_up_originals = []
            for dll in ORIGINAL_DLL_BACKUPS:
                source = directory / dll
                backup = directory / f"{dll}.b"
                if source.exists() and not backup.exists():
                    shutil.move(source, backup)
                    backed_up_originals.append(dll)
            decky.logger.info(f"Backed up original DLLs: {backed_up_originals}" if backed_up_originals else "No original DLLs required backup")

            removed_legacy = []
            for legacy in ["nvapi64.dll", "nvapi64.dll.b"]:
                legacy_path = directory / legacy
                if legacy_path.exists():
                    legacy_path.unlink()
                    removed_legacy.append(legacy)
            decky.logger.info(f"Removed legacy files: {removed_legacy}" if removed_legacy else "No legacy files to remove")

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
            if copied_support:
                decky.logger.info(f"Copied support files: {copied_support}")
            if missing_support:
                decky.logger.warning(f"Support files missing from fgmod bundle: {missing_support}")

            decky.logger.info(f"Manual patch complete for {directory}")
            return {
                "status": "success",
                "message": f"OptiScaler files copied to {directory}",
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
            for filename in set(INJECTOR_FILENAMES + SUPPORT_FILES):
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
            for dll in ORIGINAL_DLL_BACKUPS:
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
    ) -> None:
        payload = {
            "appid": str(appid),
            "game_name": game_name,
            "dll_name": dll_name,
            "target_dir": str(target_dir),
            "original_launch_options": original_launch_options,
            "backed_up_files": backed_up_files,
            "patched_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(marker_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

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

    async def manual_patch_directory(self, directory: str, dll_name: str = "dxgi.dll") -> dict:
        if dll_name not in VALID_DLL_NAMES:
            return {"status": "error", "message": f"Invalid proxy DLL name: {dll_name}"}
        try:
            target_dir = self._resolve_target_directory(directory)
        except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
            decky.logger.error(f"Manual patch validation failed: {exc}")
            return {"status": "error", "message": str(exc)}

        return self._manual_patch_directory_impl(target_dir, dll_name)

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
                    "message": "Not patched.",
                }
            metadata = self._read_marker(marker)
            dll_name = metadata.get("dll_name", "dxgi.dll")
            target_dir = Path(metadata.get("target_dir", str(marker.parent)))
            dll_present = (target_dir / dll_name).exists()
            return {
                "status": "success",
                "appid": str(appid),
                "name": game_info["name"],
                "install_found": True,
                "patched": dll_present,
                "dll_name": dll_name,
                "target_dir": str(target_dir),
                "patched_at": metadata.get("patched_at"),
                "message": (
                    f"Patched using {dll_name}."
                    if dll_present
                    else f"Marker found but {dll_name} is missing. Reinstall recommended."
                ),
            }
        except Exception as exc:
            decky.logger.error(f"[Framegen] get_game_status failed for {appid}: {exc}")
            return {"status": "error", "message": str(exc)}

    async def patch_game(self, appid: str, dll_name: str = "dxgi.dll", current_launch_options: str = "") -> dict:
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
            if existing_marker:
                metadata = self._read_marker(existing_marker)
                stored_opts = str(metadata.get("original_launch_options") or "")
                if stored_opts and not self._is_managed_launch_options(stored_opts):
                    original_launch_options = stored_opts
                try:
                    existing_marker.unlink()
                except Exception:
                    pass
            if self._is_managed_launch_options(original_launch_options):
                original_launch_options = ""

            # Auto-detect the right directory to patch
            target_dir, target_exe = self._guess_patch_target(game_info)
            decky.logger.info(f"[Framegen] patch_game: appid={appid} dll={dll_name} target={target_dir} exe={target_exe}")

            result = self._manual_patch_directory_impl(target_dir, dll_name)
            if result["status"] != "success":
                return result

            backed_up = [dll for dll in ORIGINAL_DLL_BACKUPS if (target_dir / f"{dll}.b").exists()]
            marker_path = target_dir / MARKER_FILENAME
            self._write_marker(
                marker_path,
                appid=str(appid),
                game_name=game_info["name"],
                dll_name=dll_name,
                target_dir=target_dir,
                original_launch_options=original_launch_options,
                backed_up_files=backed_up,
            )

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
                "message": f"Patched {game_info['name']} using {dll_name}.",
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

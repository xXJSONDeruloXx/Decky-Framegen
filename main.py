import decky
import os
import subprocess
import json
import shutil
import re
from pathlib import Path

# Toggle to enable overwriting the upscaler DLL from the static remote binary.
# Set to False or comment out this constant to skip the overwrite by default.
UPSCALER_OVERWRITE_ENABLED = True

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
                
            return True
        except Exception as e:
            decky.logger.error(f"Failed to copy launcher scripts: {e}")
            return False
    
    def _modify_optiscaler_ini(self, ini_file):
        """Modify OptiScaler.ini to set FGType=nukems, Fsr4Update=true, and ASI plugin settings"""
        try:
            if ini_file.exists():
                with open(ini_file, 'r') as f:
                    content = f.read()
                
                # Replace FGType=auto with FGType=nukems
                updated_content = re.sub(r'FGType\s*=\s*auto', 'FGType=nukems', content)
                
                # Replace Fsr4Update=auto with Fsr4Update=true
                updated_content = re.sub(r'Fsr4Update\s*=\s*auto', 'Fsr4Update=true', updated_content)
                
                # Replace LoadAsiPlugins=auto with LoadAsiPlugins=true
                updated_content = re.sub(r'LoadAsiPlugins\s*=\s*auto', 'LoadAsiPlugins=true', updated_content)
                
                # Replace Path=auto with Path=plugins
                updated_content = re.sub(r'Path\s*=\s*auto', 'Path=plugins', updated_content)
                
                with open(ini_file, 'w') as f:
                    f.write(updated_content)
                
                decky.logger.info("Modified OptiScaler.ini to set FGType=nukems, Fsr4Update=true, LoadAsiPlugins=true, Path=plugins")
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
            # Note: v0.9.0-pre4 includes dlssg_to_fsr3_amd_is_better.dll, fakenvapi.dll, and fakenvapi.ini in the 7z
            # Only copy files that aren't already in the archive or need to be updated
            additional_files = [
                "nvngx.dll",  # nvidia dll from streamline sdk, not bundled in opti
                "OptiPatcher_v0.30.asi"  # ASI plugin for OptiScaler spoofing
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
                asi_src = bin_path / "OptiPatcher_v0.30.asi"
                asi_dst = plugins_dir / "OptiPatcher.asi"  # Rename to generic name
                
                if asi_src.exists():
                    shutil.copy2(asi_src, asi_dst)
                    decky.logger.info(f"Copied OptiPatcher ASI to plugins directory: {asi_dst}")
                else:
                    decky.logger.warning("OptiPatcher ASI file not found in bin directory")
            except Exception as e:
                decky.logger.error(f"Failed to setup ASI plugins directory: {e}")

            decky.logger.info("Starting upscaler DLL overwrite check")
            # Optionally overwrite amd_fidelityfx_upscaler_dx12.dll with a newer static binary
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
            "fakenvapi.dll",        # v0.9.0-pre4 uses fakenvapi.dll (gets renamed to nvapi64.dll in game folder)
            "fakenvapi.ini", 
            "nvngx.dll",
            "amd_fidelityfx_dx12.dll",
            "amd_fidelityfx_framegeneration_dx12.dll",
            "amd_fidelityfx_upscaler_dx12.dll",
            "amd_fidelityfx_vk.dll", 
            "libxess.dll",
            "libxess_dx11.dll",
            "libxess_fg.dll",       # New in v0.9.0-pre4
            "libxell.dll",          # New in v0.9.0-pre4
            "fgmod",
            "fgmod-uninstaller.sh"
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

    async def list_installed_games(self) -> dict:
        try:
            steam_root = Path(decky.HOME) / ".steam" / "steam"
            library_file = Path(steam_root) / "steamapps" / "libraryfolders.vdf"
            

            if not library_file.exists():
                return {"status": "error", "message": "libraryfolders.vdf not found"}

            library_paths = []
            with open(library_file, "r", encoding="utf-8", errors="replace") as file:
                for line in file:
                    if '"path"' in line:
                        path = line.split('"path"')[1].strip().strip('"').replace("\\\\", "/")
                        library_paths.append(path)

            games = []
            for library_path in library_paths:
                steamapps_path = Path(library_path) / "steamapps"
                if not steamapps_path.exists():
                    continue

                for appmanifest in steamapps_path.glob("appmanifest_*.acf"):
                    game_info = {"appid": "", "name": ""}

                    try:
                        with open(appmanifest, "r", encoding="utf-8") as file:
                            for line in file:
                                if '"appid"' in line:
                                    game_info["appid"] = line.split('"appid"')[1].strip().strip('"')
                                if '"name"' in line:
                                    game_info["name"] = line.split('"name"')[1].strip().strip('"')
                    except UnicodeDecodeError as e:
                        decky.logger.error(f"Skipping {appmanifest} due to encoding issue: {e}")
                    finally:
                        pass  # Ensures loop continues even if an error occurs

                    if game_info["appid"] and game_info["name"]:
                        games.append(game_info)

            # Filter out games whose name contains "Proton" or "Steam Linux Runtime"
            filtered_games = [g for g in games if "Proton" not in g["name"] and "Steam Linux Runtime" not in g["name"]]

            return {"status": "success", "games": filtered_games}

        except Exception as e:
            decky.logger.error(str(e))
            return {"status": "error", "message": str(e)}

    async def log_error(self, error: str) -> None:
        decky.logger.error(f"FRONTEND: {error}")

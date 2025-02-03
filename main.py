import decky  # Old-style Decky import
import os
import subprocess
import json
from pathlib import Path

class Plugin:
    async def _main(self):
        decky.logger.info("Framegen plugin loaded")

    async def _unload(self):
        decky.logger.info("Framegen plugin unloaded.")

    async def run_uninstall_fgmod(self) -> dict:
        try:
            result = subprocess.run(
                ["/bin/bash", Path(decky.DECKY_PLUGIN_DIR) / "assets" / "fgmod-remover.sh"],
                capture_output=True,
                text=True,
                check=True
            )
            return {"status": "success", "output": result.stdout}
        except subprocess.CalledProcessError as e:
            decky.logger.error(e.output)
            return {"status": "error", "message": str(e), "output": e.output}

    async def run_install_fgmod(self) -> dict:
        try:
            assets_dir = Path(decky.DECKY_PLUGIN_DIR) / "assets"
            prepare_script = assets_dir / "prepare.sh"

            if not prepare_script.exists():
                decky.logger.error(f"prepare.sh not found: {prepare_script}")
                return {
                    "status": "error",
                    "message": f"prepare.sh not found in plugin assets."
                }

            # Ensure prepare.sh has execution permissions
            prepare_script.chmod(0o755)

            # Run prepare.sh directly from the plugin's assets folder
            process = subprocess.run(
                ["/bin/bash", str(prepare_script)],
                cwd=str(assets_dir),  # Run in assets directory to use correct paths
                capture_output=True,
                text=True,
                timeout=300
            )

            decky.logger.info(f"Script output:\n{process.stdout}")
            decky.logger.error(f"Script errors:\n{process.stderr}")

            if "All done!" not in process.stdout:
                decky.logger.error("Installation did not complete successfully")
                return {
                    "status": "error",
                    "message": process.stdout + process.stderr
                }

            return {
                "status": "success",
                "output": "You can now replace DLSS with FSR Frame Gen!"
            }

        except subprocess.TimeoutExpired:
            decky.logger.error("Installation script timed out")
            return {
                "status": "error",
                "message": "Installation timed out"
            }
        except subprocess.CalledProcessError as e:
            decky.logger.error(f"Script error: {e.stderr}")
            return {
                "status": "error",
                "message": e.stderr
            }
        except Exception as e:
            decky.logger.error(f"Unexpected error: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def check_fgmod_path(self) -> dict:
        path = Path(decky.HOME) / "fgmod"
        required_files = [
            "amd_fidelityfx_dx12.dll", "dlssg_to_fsr3_amd_is_better.dll", "libxess.dll",
            "amd_fidelityfx_vk.dll", "dlssg_to_fsr3.ini", "licenses",
            "d3dcompiler_47.dll", "dxgi.dll", "nvapi64.dll",
            "DisableNvidiaSignatureChecks.reg", "dxvk.conf", "_nvngx.dll",
            "dlss-enabler.dll", "fakenvapi.ini", "nvngx.ini",
            "dlss-enabler-upscaler.dll", "fgmod", "nvngx-wrapper.dll",
            "dlssg_to_fsr3_amd_is_better-3.0.dll", "fgmod-uninstaller.sh", "RestoreNvidiaSignatureChecks.reg"
        ]

        if path.exists():
            for file_name in required_files:
                if not path.joinpath(file_name).exists():
                    return {"exists": False}
            return {"exists": True}
        else:
            return {"exists": False}

    # New method to list installed Steam games
    async def list_installed_games(self) -> dict:
        try:
            steam_root = Path(decky.HOME) / ".steam" / "steam"
            library_file = Path(steam_root) / "steamapps" / "libraryfolders.vdf"

            if not library_file.exists():
                return {"status": "error", "message": "libraryfolders.vdf not found"}

            library_paths = []
            with open(library_file, "r", encoding="utf-8") as file:
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
                    with open(appmanifest, "r", encoding="utf-8") as file:
                        game_info = {"appid": None, "name": None}
                        for line in file:
                            if '"appid"' in line:
                                game_info["appid"] = line.split('"appid"')[1].strip().strip('"')
                            if '"name"' in line:
                                game_info["name"] = line.split('"name"')[1].strip().strip('"')

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


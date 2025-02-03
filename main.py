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
            return {"status": "error", "message": str(e), "output": e.output}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}

    async def run_install_fgmod(self) -> dict:
        try:
            defaults_dir = Path(decky.DECKY_PLUGIN_DIR) / "assets"
            fgmod_dir = Path(decky.HOME) / "fgmod"

            if not defaults_dir.exists():
                decky.logger.error(f"Defaults directory not found: {defaults_dir}")
                return {"status": "error", "message": f"Defaults directory not found: {defaults_dir}"}

            fgmod_dir.mkdir(parents=True, exist_ok=True)

            files_to_copy = [
                "amd_fidelityfx_dx12.dll", "dlssg_to_fsr3_amd_is_better.dll", "libxess.dll",
                "amd_fidelityfx_vk.dll", "dlssg_to_fsr3.ini",
                "d3dcompiler_47.dll", "dxgi.dll", "nvapi64.dll",
                "DisableNvidiaSignatureChecks.reg", "dxvk.conf", "_nvngx.dll",
                "dlss-enabler.dll", "fakenvapi.ini", "nvngx.ini",
                "dlss-enabler-upscaler.dll", "fgmod", "nvngx-wrapper.dll",
                "dlssg_to_fsr3_amd_is_better-3.0.dll", "fgmod-uninstaller.sh", "RestoreNvidiaSignatureChecks.reg"
            ]

            for file_name in files_to_copy:
                src = defaults_dir / file_name
                dest = fgmod_dir / file_name
                if not src.exists():
                    decky.logger.error(f"Required file missing: {src}")
                    return {"status": "error", "message": f"Required file missing: {file_name}"}
                dest.write_bytes(src.read_bytes())
                dest.chmod(0o755)

            # Ensure the uninstaller script is executable
            uninstaller_script = fgmod_dir / "fgmod-uninstaller.sh"
            uninstaller_script.chmod(0o755)

            # Verify all files exist in fgmod directory
            missing_files = [file for file in files_to_copy if not (fgmod_dir / file).exists()]
            if missing_files:
                return {"status": "error", "message": f"Missing files: {', '.join(missing_files)}"}

            return {"status": "success", "output": "You can now replace DLSS with FSR Frame Gen!"}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}

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
            return {"status": "error", "message": str(e)}

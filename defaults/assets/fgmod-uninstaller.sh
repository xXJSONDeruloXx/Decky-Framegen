#!/usr/bin/env bash

set -x  # Enable debugging
exec > >(tee -i /tmp/prepare.log) 2>&1  # Log output and errors

error_exit() {
  echo "$1"
  if [[ -n $STEAM_ZENITY ]]; then
    $STEAM_ZENITY --error --text "$1"
  else 
    zenity --error --text "$1"
  fi
  exit 1
}

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 program [program_arguments...]"
  exit 1
fi

game_path=""
mod_path="/usr/share/fgmod"

# Locate the game folder based on the first argument
if [[ "$1" == *.exe ]]; then
  exe_folder_path=$(dirname "$1")
else
  for arg in "$@"; do
    if [[ "$arg" == *.exe ]]; then
      # Handle special cases for specific games
      [[ "$arg" == *"Cyberpunk 2077"* ]] && arg=${arg//REDprelauncher.exe/bin/x64/Cyberpunk2077.exe}
      [[ "$arg" == *"Witcher 3"* ]]      && arg=${arg//REDprelauncher.exe/bin/x64_dx12/witcher3.exe}
      [[ "$arg" == *"HITMAN 3"* ]]       && arg=${arg//Launcher.exe/Retail/HITMAN3.exe}
      [[ "$arg" == *"HITMAN World of Assassination"* ]] && arg=${arg//Launcher.exe/Retail/HITMAN3.exe}
      [[ "$arg" == *"SYNCED"* ]]         && arg=${arg//Launcher\/sop_launcher.exe/SYNCED.exe}
      [[ "$arg" == *"2KLauncher"* ]]     && arg=${arg//2KLauncher\/LauncherPatcher.exe/DoesntMatter.exe}
      [[ "$arg" == *"Warhammer 40,000 DARKTIDE"* ]] && arg=${arg//launcher\/Launcher.exe/binaries/Darktide.exe}
      [[ "$arg" == *"Warhammer Vermintide 2"* ]]    && arg=${arg//launcher\/Launcher.exe/binaries_dx12/vermintide2_dx12.exe}
      [[ "$arg" == *"Satisfactory"* ]]   && arg=${arg//FactoryGameSteam.exe/Engine/Binaries/Win64/FactoryGameSteam-Win64-Shipping.exe}
      exe_folder_path=$(dirname "$arg")
      break
    fi
  done
fi

# Fallback to STEAM_COMPAT_INSTALL_PATH when no path was found
if [[ ! -d $exe_folder_path ]] && [[ -n ${STEAM_COMPAT_INSTALL_PATH} ]]; then
  exe_folder_path=${STEAM_COMPAT_INSTALL_PATH}
fi

# Check for Unreal Engine game paths
if [[ -d "$exe_folder_path/Engine" ]]; then
  ue_exe_path=$(find "$exe_folder_path" -maxdepth 4 -mindepth 4 -path "*Binaries/Win64/*.exe" -not -path "*/Engine/*" | head -1)
  exe_folder_path=$(dirname "$ue_exe_path")
fi

# Verify the game folder exists
if [[ ! -d $exe_folder_path ]]; then
  error_exit "Unable to locate the game folder. Ensure the game is installed and the path is correct."
fi

# Avoid operating on the uninstaller's own directory
script_dir=$(dirname "$(realpath "$0")")
if [[ "$(realpath "$exe_folder_path")" == "$script_dir" ]]; then
  error_exit "The target directory matches the script's directory. Aborting to prevent accidental deletion."
fi

# Change to the game directory
cd "$exe_folder_path" || error_exit "Failed to change directory to $exe_folder_path"

# Verify current directory before proceeding
if [[ "$(pwd)" != "$exe_folder_path" ]]; then
  error_exit "Unexpected working directory: $(pwd)"
fi

# Log the resolved exe_folder_path for debugging
echo "Resolved exe_folder_path: $exe_folder_path" >> /tmp/fgmod-uninstaller.log

# Perform uninstallation
rm -f "dlss-enabler.dll" "dxgi.dll" "nvngx-wrapper.dll" "_nvngx.dll"
rm -f "dlssg_to_fsr3_amd_is_better.dll" "dlssg_to_fsr3_amd_is_better-3.0.dll"
rm -f "dlss-enabler-upscaler.dll" "nvngx.ini" "libxess.dll"
rm -f "d3dcompiler_47.dll" "amd_fidelityfx_dx12.dll" "amd_fidelityfx_vk.dll"
rm -f "nvapi64.dll" "fakenvapi.ini" "OptiScaler.log"
rm -f "dlss-enabler.log" "dlssg_to_fsr3.log" "fakenvapi.log"

# Restore original DLLs if they exist
mv -f "libxess.dll.b" "libxess.dll" 2>/dev/null
mv -f "d3dcompiler_47.dll.b" "d3dcompiler_47.dll" 2>/dev/null
mv -f "amd_fidelityfx_dx12.dll.b" "amd_fidelityfx_dx12.dll" 2>/dev/null
mv -f "amd_fidelityfx_vk.dll.b" "amd_fidelityfx_vk.dll" 2>/dev/null

# Self-remove uninstaller (now optional for safety)
echo "Uninstaller self-removal skipped for safety. Remove manually if needed."

echo "fgmod removed from this game."

if [[ $# -gt 1 ]]; then
  echo "Launching the game..."
  export SteamDeck=0
  export WINEDLLOVERRIDES="${WINEDLLOVERRIDES},dxgi=n,b"
  exec "$@"
else
  echo "Uninstallation complete. No game specified to run."
fi
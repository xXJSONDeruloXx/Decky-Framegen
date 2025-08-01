#!/usr/bin/env bash

set -x
exec > >(tee -i /tmp/fgmod-uninstaller.log) 2>&1

error_exit() {
  echo "❌ $1"
  if [[ -n $STEAM_ZENITY ]]; then
    $STEAM_ZENITY --error --text "$1"
  else 
    zenity --error --text "$1" || echo "Zenity failed to display error"
  fi
  logger -t fgmod-uninstaller "❌ ERROR: $1"
  exit 1
}

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 program [program_arguments...]"
  exit 1
fi

# === Resolve Game Path ===
exe_folder_path=""
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
[[ -z "$exe_folder_path" && -n "$STEAM_COMPAT_INSTALL_PATH" ]] && exe_folder_path="$STEAM_COMPAT_INSTALL_PATH"

# Check for Unreal Engine game paths
if [[ -d "$exe_folder_path/Engine" ]]; then
  ue_exe_path=$(find "$exe_folder_path" -maxdepth 4 -mindepth 4 -path "*Binaries/Win64/*.exe" -not -path "*/Engine/*" | head -1)
  exe_folder_path=$(dirname "$ue_exe_path")
fi

# Verify the game folder exists
[[ ! -d "$exe_folder_path" ]] && error_exit "Unable to locate the game folder: $exe_folder_path"

# Avoid operating on the uninstaller's own directory
script_dir=$(dirname "$(realpath "$0")")
[[ "$(realpath "$exe_folder_path")" == "$script_dir" ]] && error_exit "The target directory matches the script's directory. Aborting to prevent accidental deletion."

# Change to the game directory
cd "$exe_folder_path" || error_exit "Failed to change directory to $exe_folder_path"

# Verify current directory before proceeding
[[ "$(pwd)" != "$exe_folder_path" ]] && error_exit "Unexpected working directory: $(pwd)"

logger -t fgmod-uninstaller "🟢 Uninstalling from: $exe_folder_path"

# === Remove OptiScaler Files ===
echo "🧹 Removing OptiScaler files..."
rm -f "OptiScaler.dll" "dxgi.dll" "winmm.dll" "dbghelp.dll" "version.dll" "wininet.dll" "winhttp.dll" "OptiScaler.asi"
rm -f "OptiScaler.ini" "OptiScaler.log"

# === Remove Nukem FG Mod Files ===
echo "🧹 Removing Nukem FG Mod files..."
rm -f "dlssg_to_fsr3_amd_is_better.dll" "dlssg_to_fsr3.ini" "dlssg_to_fsr3.log"
rm -f "nvapi64.dll" "fakenvapi.ini" "fakenvapi.log"
rm -f "amdxcffx64.dll"

# === Remove Supporting Libraries ===
echo "🧹 Removing supporting libraries..."
rm -f "libxess.dll" "nvngx.dll" "nvngx.ini"

# === Remove Legacy Files ===
echo "🧹 Removing legacy files..."
rm -f "dlss-enabler.dll" "dlss-enabler-upscaler.dll" "dlss-enabler.log"
rm -f "nvngx-wrapper.dll" "_nvngx.dll"
rm -f "dlssg_to_fsr3_amd_is_better-3.0.dll"

# === Restore Original DLLs ===
echo "🔄 Restoring original DLLs..."
original_dlls=("d3dcompiler_47.dll" "amd_fidelityfx_dx12.dll" "amd_fidelityfx_vk.dll" "nvapi64.dll" "amdxcffx64.dll" "libxess.dll")
for dll in "${original_dlls[@]}"; do
  if [[ -f "${dll}.b" ]]; then
    mv "${dll}.b" "$dll"
    echo "✅ Restored original $dll"
    logger -t fgmod-uninstaller "✅ Restored original $dll"
  fi
done

# === Self-remove uninstaller ===
echo "🗑️ Removing uninstaller..."
rm -f "fgmod-uninstaller.sh"

echo "✅ fgmod removed from this game successfully!"
logger -t fgmod-uninstaller "✅ fgmod removed from $exe_folder_path"

# === Execute original command if provided ===
if [[ $# -gt 1 ]]; then
  echo "🚀 Launching the game..."
  export SteamDeck=0
  export WINEDLLOVERRIDES="${WINEDLLOVERRIDES},dxgi=n,b"
  exec "$@"
else
  echo "✅ Uninstallation complete. No game specified to run."
fi
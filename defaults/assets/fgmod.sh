#!/usr/bin/env bash

set -x
exec > >(tee -i /tmp/fgmod-install.log) 2>&1

error_exit() {
  echo "❌ $1"
  if [[ -n $STEAM_ZENITY ]]; then
    $STEAM_ZENITY --error --text "$1"
  else 
    zenity --error --text "$1" || echo "Zenity failed to display error"
  fi
  logger -t fgmod "❌ ERROR: $1"
  exit 1
}

# === CONFIG ===
fgmod_path="$HOME/fgmod"
dll_name="${DLL:-dxgi.dll}"
preserve_ini="${PRESERVE_INI:-true}"

# === Resolve Game Path ===
if [[ "$#" -lt 1 ]]; then
  error_exit "Usage: $0 program [program_arguments...]"
fi

exe_folder_path=""
if [[ $# -eq 1 ]]; then
  [[ "$1" == *.exe ]] && exe_folder_path=$(dirname "$1") || exe_folder_path="$1"
else
  for arg in "$@"; do
    if [[ "$arg" == *.exe ]]; then
      [[ "$arg" == *"Cyberpunk 2077"* ]] && arg=${arg//REDprelauncher.exe/bin/x64/Cyberpunk2077.exe}
      [[ "$arg" == *"Witcher 3"* ]]      && arg=${arg//REDprelauncher.exe/bin/x64_dx12/witcher3.exe}
      [[ "$arg" == *"Baldurs Gate 3"* ]] && arg=${arg//Launcher\/LariLauncher.exe/bin/bg3_dx11.exe}
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

[[ -z "$exe_folder_path" && -n "$STEAM_COMPAT_INSTALL_PATH" ]] && exe_folder_path="$STEAM_COMPAT_INSTALL_PATH"

if [[ -d "$exe_folder_path/Engine" ]]; then
  ue_exe=$(find "$exe_folder_path" -maxdepth 4 -mindepth 4 -path "*Binaries/Win64/*.exe" -not -path "*/Engine/*" | head -1)
  exe_folder_path=$(dirname "$ue_exe")
fi

[[ ! -d "$exe_folder_path" ]] && error_exit "❌ Could not resolve game directory!"
[[ ! -w "$exe_folder_path" ]] && error_exit "🛑 No write permission to the game folder!"

logger -t fgmod "🟢 Target directory: $exe_folder_path"
logger -t fgmod "🧩 Using DLL name: $dll_name"
logger -t fgmod "📄 Preserve INI: $preserve_ini"

# === Cleanup Old Injectors ===
rm -f "$exe_folder_path"/{dxgi.dll,winmm.dll,nvngx.dll,_nvngx.dll,nvngx-wrapper.dll,dlss-enabler.dll,OptiScaler.dll}

# === Optional: Backup Original DLLs ===
original_dlls=("d3dcompiler_47.dll" "amd_fidelityfx_dx12.dll" "amd_fidelityfx_framegeneration_dx12.dll" "amd_fidelityfx_upscaler_dx12.dll" "amd_fidelityfx_vk.dll" "nvapi64.dll")
for dll in "${original_dlls[@]}"; do
  [[ -f "$exe_folder_path/$dll" && ! -f "$exe_folder_path/$dll.b" ]] && mv -f "$exe_folder_path/$dll" "$exe_folder_path/$dll.b"
done

# === Core Install ===
if [[ -f "$fgmod_path/renames/$dll_name" ]]; then
  echo "✅ Using pre-renamed $dll_name"
  cp "$fgmod_path/renames/$dll_name" "$exe_folder_path/$dll_name" || error_exit "❌ Failed to copy $dll_name"
else
  echo "⚠️ Pre-renamed $dll_name not found, falling back to OptiScaler.dll"
  cp "$fgmod_path/OptiScaler.dll" "$exe_folder_path/$dll_name" || error_exit "❌ Failed to copy OptiScaler.dll as $dll_name"
fi

# === OptiScaler.ini Handling ===
if [[ "$preserve_ini" == "true" && -f "$exe_folder_path/OptiScaler.ini" ]]; then
  echo "📄 Preserving existing OptiScaler.ini (user settings retained)"
  logger -t fgmod "📄 Existing OptiScaler.ini preserved in $exe_folder_path"
else
  echo "📄 Installing OptiScaler.ini from plugin defaults"
  cp "$fgmod_path/OptiScaler.ini" "$exe_folder_path/OptiScaler.ini" || error_exit "❌ Failed to copy OptiScaler.ini"
  logger -t fgmod "📄 OptiScaler.ini installed to $exe_folder_path"
fi

# === Supporting Libraries ===
cp -f "$fgmod_path/libxess.dll" "$exe_folder_path/" || true
cp -f "$fgmod_path/libxess_dx11.dll" "$exe_folder_path/" || true
cp -f "$fgmod_path/libxess_fg.dll" "$exe_folder_path/" || true
cp -f "$fgmod_path/libxell.dll" "$exe_folder_path/" || true
cp -f "$fgmod_path/amd_fidelityfx_dx12.dll" "$exe_folder_path/" || true
cp -f "$fgmod_path/amd_fidelityfx_framegeneration_dx12.dll" "$exe_folder_path/" || true
cp -f "$fgmod_path/amd_fidelityfx_upscaler_dx12.dll" "$exe_folder_path/" || true
cp -f "$fgmod_path/amd_fidelityfx_vk.dll" "$exe_folder_path/" || true
cp -f "$fgmod_path/nvngx.dll" "$exe_folder_path/" || true

# === Nukem FG Mod Files (now in fgmod directory) ===
cp -f "$fgmod_path/dlssg_to_fsr3_amd_is_better.dll" "$exe_folder_path/" || true
# cp -f "$fgmod_path/dlssg_to_fsr3.ini" "$exe_folder_path/" || true

# Note: dlssg_to_fsr3.ini is not included in v0.9.0-pre4 archive
# Copy fakenvapi.dll as nvapi64.dll (v1.3.8.1) - this replaces the real NVIDIA API
if [[ -f "$fgmod_path/fakenvapi.dll" ]]; then
  cp -f "$fgmod_path/fakenvapi.dll" "$exe_folder_path/nvapi64.dll" || true
  echo "📦 Installed fakenvapi.dll as nvapi64.dll"
else
  # Legacy fallback for older setups
  cp -f "$fgmod_path/nvapi64.dll" "$exe_folder_path/" || true
  echo "📦 Using legacy nvapi64.dll"
fi
cp -f "$fgmod_path/fakenvapi.ini" "$exe_folder_path/" || true

# === Additional Support Files ===
# cp -f "$fgmod_path/d3dcompiler_47.dll" "$exe_folder_path/" || true

# Note: d3dcompiler_47.dll is not included in v0.9.0-pre4 archive

echo "✅ Installation completed successfully!"
echo "📄 For Steam, add this to the launch options: \"$fgmod_path/fgmod\" %COMMAND%"
echo "📄 For Heroic, add this as a new wrapper: \"$fgmod_path/fgmod\""
logger -t fgmod "🟢 Installation completed successfully for $exe_folder_path"

# === Execute original command ===
if [[ $# -gt 1 ]]; then
  # Log to both file and system journal
  logger -t fgmod "=================="
  logger -t fgmod "Debug Info (Launch Mode):"
  logger -t fgmod "Number of arguments: $#"
  for i in $(seq 1 $#); do
    logger -t fgmod "Arg $i: ${!i}"
  done
  logger -t fgmod "Final executable path: $exe_folder_path"
  logger -t fgmod "=================="
  
  # Execute the original command
  export SteamDeck=0
  export WINEDLLOVERRIDES="$WINEDLLOVERRIDES,dxgi=n,b"
  exec "$@"
else
  echo "Done!"
  echo "----------------------------------------"
  echo "Debug Info (Standalone Mode):"
  echo "Number of arguments: $#"
  for i in $(seq 1 $#); do
    echo "Arg $i: ${!i}"
  done
  echo "Final executable path: $exe_folder_path"
  echo "----------------------------------------"
  
  # Also log standalone mode to journal
  logger -t fgmod "=================="
  logger -t fgmod "Debug Info (Standalone Mode):"
  logger -t fgmod "Number of arguments: $#"
  for i in $(seq 1 $#); do
    logger -t fgmod "Arg $i: ${!i}"
  done
  logger -t fgmod "Final executable path: $exe_folder_path"
  logger -t fgmod "=================="
fi

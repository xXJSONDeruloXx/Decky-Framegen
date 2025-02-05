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

mod_path="/usr/share/fgmod"

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 program [program_arguments...]"
    exit 1
fi

# One arg means the command is ran standalone
if [[ $# -eq 1 ]]; then
  if [[ "$1" == *.exe ]]; then
    exe_folder_path=$(dirname "$1")
  else
    exe_folder_path=$1
  fi
else
  for arg in "$@"; do
    if [[ "$arg" == *.exe ]]; then
      # Special cases, only FG-supported games
      [[ "$arg" == *"Cyberpunk 2077"* ]] && arg=${arg//REDprelauncher.exe/bin/x64/Cyberpunk2077.exe}
      [[ "$arg" == *"Witcher 3"* ]]      && arg=${arg//REDprelauncher.exe/bin/x64_dx12/witcher3.exe}
      [[ "$arg" == *"HITMAN 3"* ]]       && arg=${arg//Launcher.exe/Retail/HITMAN3.exe}
      [[ "$arg" == *"HITMAN World of Assassination"* ]] && arg=${arg//Launcher.exe/Retail/HITMAN3.exe}
      [[ "$arg" == *"SYNCED"* ]]         && arg=${arg//Launcher\/sop_launcher.exe/SYNCED.exe} # UE with a launcher
      [[ "$arg" == *"2KLauncher"* ]]     && arg=${arg//2KLauncher\/LauncherPatcher.exe/DoesntMatter.exe} # 2K launcher games
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
  echo "Trying the path from STEAM_COMPAT_INSTALL_PATH"
  exe_folder_path=${STEAM_COMPAT_INSTALL_PATH}
fi

# Check for UE games
if [[ -d "$exe_folder_path/Engine" ]]; then
  ue_exe_path=$(find "$exe_folder_path" -maxdepth 4 -mindepth 4 -path "*Binaries/Win64/*.exe" -not -path "*/Engine/*" | head -1)
  exe_folder_path=$(dirname "$ue_exe_path")
fi

if [[ -d $exe_folder_path ]]; then
  if [[ ! -w $exe_folder_path ]]; then
    error_exit "No write permission to the game folder!"
  fi

  original_dlls=("libxess.dll" "d3dcompiler_47.dll" "amd_fidelityfx_dx12.dll" "amd_fidelityfx_vk.dll")

  # Assume that the mod is not installed when dlss-enabler.dll is not present
  if [[ ! -f "$exe_folder_path/dlss-enabler.dll" ]]; then
    [[ -f "$exe_folder_path/dxgi.dll" ]] && error_exit 'dxgi.dll is already present in the game folder!\nThis script uses dxgi.dll to load required files.\nRemove the mod using dxgi.dll or install DLSS Enabler manually.'
    for dll in "${original_dlls[@]}"; do
      if [[ ! -f "$exe_folder_path/${dll}.b" ]]; then
        mv -f "$exe_folder_path/$dll" "$exe_folder_path/${dll}.b" 2>/dev/null
      fi
    done
  fi

  cp -f "$mod_path/fgmod-uninstaller.sh" "$exe_folder_path" ||
  error_exit "Couldn't copy the uninstaller!"

  cp -f "$mod_path/dlss-enabler.dll"  "$exe_folder_path" &&
  cp -f "$mod_path/dxgi.dll"          "$exe_folder_path" &&
  cp -f "$mod_path/nvngx-wrapper.dll" "$exe_folder_path" ||
  error_exit "Couldn't copy DLSS Enabler files!"

  # File is not preset on Nvidia installs so will fail on some setups on purpose
  cp -f "$mod_path/nvapi64.dll" "$exe_folder_path" 2>/dev/null

  cp -f "$mod_path/_nvngx.dll" "$exe_folder_path" ||
  error_exit "Couldn't copy _nvngx.dll!"

  cp -f "$mod_path/dlssg_to_fsr3_amd_is_better.dll"     "$exe_folder_path" &&
  cp -f "$mod_path/dlssg_to_fsr3_amd_is_better-3.0.dll" "$exe_folder_path" ||
  error_exit "Couldn't copy dlssg-to-fsr3!"

  cp -f "$mod_path/dlss-enabler-upscaler.dll" "$exe_folder_path" &&
  cp -f "$mod_path/amd_fidelityfx_dx12.dll"   "$exe_folder_path" &&
  cp -f "$mod_path/amd_fidelityfx_vk.dll"     "$exe_folder_path" &&
  cp -f "$mod_path/libxess.dll"               "$exe_folder_path" &&
  cp -f "$mod_path/d3dcompiler_47.dll"        "$exe_folder_path" ||
  error_exit "Couldn't copy Optiscaler files!"

  cp -n "$mod_path/nvngx.ini"                 "$exe_folder_path"
  cp -n "$mod_path/fakenvapi.ini"             "$exe_folder_path"
else
  error_exit "Path doesn't exist!"
fi

if [[ $# -gt 1 ]]; then
  # Execute the original command
  export SteamDeck=0
  export WINEDLLOVERRIDES="$WINEDLLOVERRIDES,dxgi=n,b"
  "$@"
else
  echo Done!
fi

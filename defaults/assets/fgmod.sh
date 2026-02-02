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
opti_path="$fgmod_path/opti"
int8_path="$fgmod_path/int8"

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
      [[ "$arg" == *"FINAL FANTASY XIV Online"* ]] && arg=${arg//boot\/ffxivboot.exe/game/ffxiv_dx11.exe}
      exe_folder_path=$(dirname "$arg")
      break
    fi
  done
fi

for arg in "$@"; do
  if [[ "$arg" == lutris:rungameid/* ]]; then
    lutris_id="${arg#lutris:rungameid/}"

    # Get slug from Lutris JSON
    slug=$(lutris --list-games --json 2>/dev/null | jq -r ".[] | select(.id == $lutris_id) | .slug")

    if [[ -z "$slug" || "$slug" == "null" ]]; then
      echo "Could not find slug for Lutris ID $lutris_id"
      break
    fi

    # Find matching YAML file using slug
    config_file=$(find ~/.config/lutris/games/ -iname "${slug}-*.yml" | head -1)

    if [[ -z "$config_file" ]]; then
      echo "No config file found for slug '$slug'"
      break
    fi

    # Extract executable path from YAML
    exe_path=$(grep -E '^\s*exe:' "$config_file" | sed 's/.*exe:[[:space:]]*//')

    if [[ -n "$exe_path" ]]; then
      exe_folder_path=$(dirname "$exe_path")
      echo "Resolved executable path: $exe_path"
      echo "Executable folder: $exe_folder_path"
    else
      echo "Executable path not found in $config_file"
    fi

    break
  fi
done

[[ -z "$exe_folder_path" && -n "$STEAM_COMPAT_INSTALL_PATH" ]] && exe_folder_path="$STEAM_COMPAT_INSTALL_PATH"

if [[ -d "$exe_folder_path/Engine" ]]; then
  ue_exe=$(find "$exe_folder_path" -maxdepth 4 -mindepth 4 -path "*Binaries/Win64/*.exe" -not -path "*/Engine/*" | head -1)
  exe_folder_path=$(dirname "$ue_exe")
fi

[[ ! -d "$exe_folder_path" ]] && error_exit "❌ Could not resolve game directory!"
[[ ! -w "$exe_folder_path" ]] && error_exit "🛑 No write permission to the game folder!"

logger -t fgmod "🟢 Target directory: $exe_folder_path"

# === Copy all OptiScaler files from ~/fgmod/opti to game directory ===
echo "📦 Copying OptiScaler files from $opti_path to $exe_folder_path"
if [[ ! -d "$opti_path" ]]; then
  error_exit "❌ OptiScaler directory not found at $opti_path. Please run Setup OptiScaler first."
fi

# Copy all files from opti directory to game directory
cp -rf "$opti_path"/* "$exe_folder_path/" || error_exit "❌ Failed to copy OptiScaler files"
echo "✅ Copied all OptiScaler files to game directory"

# === Copy int8 upscaler DLL if it exists ===
if [[ -f "$int8_path/amd_fidelityfx_upscaler_dx12.dll" ]]; then
  echo "📦 Copying int8 upscaler DLL to $exe_folder_path"
  cp -f "$int8_path/amd_fidelityfx_upscaler_dx12.dll" "$exe_folder_path/" || true
  echo "✅ Copied int8 upscaler DLL"
fi

# === Apply OptiScaler setup (what setup_linux.sh does) ===
# We do this directly instead of running setup_linux.sh to avoid interaction issues
echo "🔧 Setting up OptiScaler files"

# Rename OptiScaler.dll to dxgi.dll (equivalent to selecting option 1)
if [[ -f "$exe_folder_path/OptiScaler.dll" ]]; then
  if [[ -f "$exe_folder_path/dxgi.dll" ]]; then
    echo "⚠️ Removing existing dxgi.dll"
    rm -f "$exe_folder_path/dxgi.dll"
  fi
  mv "$exe_folder_path/OptiScaler.dll" "$exe_folder_path/dxgi.dll"
  echo "✅ Renamed OptiScaler.dll to dxgi.dll"
else
  echo "⚠️ OptiScaler.dll not found, may already be renamed"
fi

# Disable spoofing for non-Nvidia (equivalent to answering 'n' then 'y')
# The script asks: "Are you using Nvidia?" - we answer 'n'
# Then asks: "Will you try to use DLSS inputs?" - we answer 'y' (enable spoofing)
# Spoofing stays enabled (Dxgi=auto), so we don't need to change OptiScaler.ini

# Clean up setup script and windows batch file
rm -f "$exe_folder_path/setup_linux.sh" "$exe_folder_path/setup_windows.bat"
rm -f "$exe_folder_path/!! EXTRACT ALL FILES TO GAME FOLDER !!"

# Create uninstaller script (simplified version)
cat > "$exe_folder_path/remove_optiscaler.sh" << 'UNINSTALL_EOF'
#!/usr/bin/env bash
echo "Removing OptiScaler files..."
rm -f OptiScaler.log OptiScaler.ini dxgi.dll fakenvapi.dll fakenvapi.ini fakenvapi.log
rm -f dlssg_to_fsr3_amd_is_better.dll dlssg_to_fsr3.log
rm -rf D3D12_Optiscaler DlssOverrides Licenses
echo "OptiScaler removed!"
rm -f "$0"
UNINSTALL_EOF
chmod +x "$exe_folder_path/remove_optiscaler.sh"

echo "✅ OptiScaler setup completed"

echo "✅ Installation completed successfully!"
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
  
  # Execute the original command with proper environment variables
  export SteamDeck=0
  export WINEDLLOVERRIDES="dxgi=n,b${WINEDLLOVERRIDES:+,$WINEDLLOVERRIDES}"
  
  # Filter out leading -- separators (from Steam launch options)
  while [[ $# -gt 0 && "$1" == "--" ]]; do
    shift
  done
  
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
fi

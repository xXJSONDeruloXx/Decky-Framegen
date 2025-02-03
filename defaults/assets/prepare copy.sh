#!/usr/bin/env bash

set -x  # Enable debugging
exec > >(tee -i /tmp/prepare.log) 2>&1  # Log output and errors

mod_path="$HOME/fgmod"
bin_path="$(dirname "$(realpath "$0")")/../bin"
assets_path="$(dirname "$(realpath "$0")")"

nvidiaver="NVIDIA-Linux-x86_64-555.52.04.run"
enablerver="dlss-enabler-setup-3.02.000.0.exe"
fakenvapiver="fakenvapi.7z"
standalone=1

if [[ -d "$mod_path" ]] && [[ ! $mod_path == . ]]; then
    rm -r "$mod_path"
fi

mkdir -p "$mod_path"
cd "$mod_path" || exit 1

# Copy required files from bin directory
cp "$bin_path/$enablerver" .
cp "$bin_path/$nvidiaver" .
cp "$bin_path/d3dcompiler_47.dll" .
cp "$bin_path/innoextract" .
cp "$bin_path/$fakenvapiver" .

# Copy fgmod.sh and fgmod-uninstaller.sh from defaults/assets
cp "$assets_path/fgmod.sh" "$mod_path/fgmod" || exit 1
cp "$assets_path/fgmod-uninstaller.sh" "$mod_path" || exit 1

if [[ ! -f "$enablerver" || ! -f "$nvidiaver" || ! -f "d3dcompiler_47.dll" || ! -f "innoextract" || ! -f "$fakenvapiver" || ! -f "fgmod" || ! -f "fgmod-uninstaller.sh" ]]; then
    echo "Missing one or more required files. Exiting."
    exit 1
fi

# Extract files
chmod +x "$nvidiaver"
./"$nvidiaver" -x

chmod +x innoextract
./innoextract "$enablerver"

# Prepare mod files
mv app/* .
rm -r app
[[ -f "$(which 7z 2>/dev/null)" ]] && 7z -y x "$fakenvapiver"
cp -f NVIDIA-Linux-x86_64-555.52.04/nvngx.dll _nvngx.dll
cp -f NVIDIA-Linux-x86_64-555.52.04/LICENSE "licenses/LICENSE (NVIDIA driver)"
chmod +r _nvngx.dll

# Cleanup
rm -rf innoextract NVIDIA-Linux-x86_64-555.52.04 dlss-enabler-setup-3.02.000.0.exe NVIDIA-Linux-x86_64-555.52.04.run fakenvapi.7z
rm -rf plugins nvapi64-proxy.dll dlss-enabler-fsr.dll dlss-enabler-xess.dll dbghelp.dll version.dll winmm.dll nvngx.dll \
       dlss-finder.exe dlss-enabler.log dlssg_to_fsr3.log fakenvapi.log "LICENSE (DLSSG to FSR3 mod).txt" \
       "Readme (DLSS enabler).txt" "READ ME (DLSSG to FSR3 mod).txt" "XESS LICENSE.pdf"
[[ -f "$(which nvidia-smi 2>/dev/null)" ]] && rm -rf nvapi64.dll fakenvapi.ini

# Update paths in scripts
sed -i 's|mod_path="/usr/share/fgmod"|mod_path="'"$mod_path"'"|g' fgmod
chmod +x fgmod

sed -i 's|mod_path="/usr/share/fgmod"|mod_path="'"$mod_path"'"|g' fgmod-uninstaller.sh
chmod +x fgmod-uninstaller.sh

echo ""

# Flatpak compatibility
if flatpak list | grep "com.valvesoftware.Steam" 1>/dev/null; then
    echo "Flatpak version of Steam detected, adding access to fgmod's folder"
    echo "Please restart Steam!"
    flatpak override --user --filesystem="$mod_path" com.valvesoftware.Steam
fi

echo "For Steam, add this to the launch options: \"$mod_path/fgmod\" %COMMAND%"
echo "For Heroic, add this as a new wrapper: \"$mod_path/fgmod\""
echo "All done!"
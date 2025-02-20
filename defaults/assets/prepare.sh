#!/usr/bin/env bash

set -x  # Enable debugging
exec > >(tee -i /tmp/prepare.log) 2>&1  # Log output and errors

mod_path="$HOME/fgmod-plus"
bin_path="$(dirname "$(realpath "$0")")/../bin"
assets_path="$(dirname "$(realpath "$0")")"

standalone=1

if [[ -d "$mod_path" ]] && [[ ! $mod_path == . ]]; then
    rm -r "$mod_path"
fi

mkdir -p "$mod_path"
cd "$mod_path" || exit 1

# Copy all files from bin directory into the current directory
cp "$bin_path"/* .

# Create temporary directory for asset download
temp_dir=$(mktemp -d)
cd "$temp_dir" || exit 1

# Download the latest OptiScaler nightly release
echo "Downloading OptiScaler..."
# First get the latest release assets URL
if ! latest_url=$(wget -qO- https://api.github.com/repos/cdozdil/OptiScaler/releases/tags/nightly | grep -o 'https://.*\.7z' | head -n1); then
    echo "Error: Failed to fetch latest release URL"
    exit 1
fi

echo "Downloading from: $latest_url"
if ! wget -q --show-progress -O optiscaler.7z "$latest_url"; then
    echo "Error: Failed to download OptiScaler"
    exit 1
fi

# Verify the download
if [ ! -f optiscaler.7z ] || [ ! -s optiscaler.7z ]; then
    echo "Error: Download file is missing or empty"
    exit 1
fi

# Extract the 7z file
echo "Extracting nvngx.dll..."
7z e optiscaler.7z nvngx.dll

# Rename and move the DLL to mod path
if [ -f nvngx.dll ]; then
    mv nvngx.dll "$mod_path/dlss-enabler-upscaler.dll"
    echo "Successfully installed dlss-enabler-upscaler.dll"
else
    echo "Error: Failed to extract nvngx.dll"
    exit 1
fi

# Clean up
cd "$mod_path" || exit 1
rm -rf "$temp_dir"

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
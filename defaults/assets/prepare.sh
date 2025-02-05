#!/usr/bin/env bash

set -x  # Enable debugging
exec > >(tee -i /tmp/prepare.log) 2>&1  # Log output and errors

mod_path="$HOME/fgmod"
bin_path="$(dirname "$(realpath "$0")")/../bin"
assets_path="$(dirname "$(realpath "$0")")"

standalone=1

if [[ -d "$mod_path" ]] && [[ ! $mod_path == . ]]; then
    rm -r "$mod_path"
fi

mkdir -p "$mod_path"
cd "$mod_path" || exit 1

# Copy required files from bin directory into the current directory
cp "$bin_path/assets.zip" .

# Unzip assets.zip so that all files are in the modpath root, then remove the zip file
unzip -j -o assets.zip && rm assets.zip

# Copy fgmod.sh and fgmod-uninstaller.sh from defaults/assets
cp "$assets_path/fgmod.sh" "$mod_path/fgmod" || exit 1
cp "$assets_path/fgmod-uninstaller.sh" "$mod_path" || exit 1

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
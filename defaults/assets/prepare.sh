#!/usr/bin/env bash

set -x  # Enable debugging
exec > >(tee -i /tmp/prepare.log) 2>&1  # Log output and errors

# Function to test if curl works with a given LD_LIBRARY_PATH
test_curl() {
    local lib_path=$1
    export LD_LIBRARY_PATH=$lib_path:$LD_LIBRARY_PATH
    echo "Testing curl with LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
    curl --version >/dev/null 2>&1
    return $?
}

# Try library paths and choose the one that works
if test_curl "/usr/lib"; then
    echo "Using OpenSSL library path: /usr/lib"
    export LD_LIBRARY_PATH="/usr/lib:$LD_LIBRARY_PATH"
elif test_curl "/usr/lib64"; then
    echo "Using OpenSSL library path: /usr/lib64"
    export LD_LIBRARY_PATH="/usr/lib64:$LD_LIBRARY_PATH"
elif test_curl "/lib"; then
    echo "Using OpenSSL library path: /lib"
    export LD_LIBRARY_PATH="/usr/lib:$LD_LIBRARY_PATH"
elif test_curl "/lib64"; then
    echo "Using OpenSSL library path: /lib64"
    export LD_LIBRARY_PATH="/usr/lib64:$LD_LIBRARY_PATH"
elif test_curl "/usr/local/lib"; then
    echo "Using OpenSSL library path: /usr/local/lib"
    export LD_LIBRARY_PATH="/usr/local/lib:$LD_LIBRARY_PATH"
elif test_curl "/usr/local/ssl/lib"; then
    echo "Using OpenSSL library path: /usr/local/ssl/lib"
    export LD_LIBRARY_PATH="/usr/local/ssl/lib:$LD_LIBRARY_PATH"
else
    echo "Failed to configure OpenSSL for curl. Exiting."
    exit 1
fi

mod_path="$HOME/fgmod"
nvidiaver=555.52.04
enablerver=3.02.000.0
fakenvapiver=v1.2.0
standalone=1

if [[ -d "$mod_path" ]] && [[ ! $mod_path == . ]]; then
    rm -r "$mod_path"
fi

# In case script gets ran from a different directory
cd "$(dirname "$0")"

mkdir -p "$mod_path"
if [[ ! $standalone -eq 0 ]]; then
    [[ -f fgmod.sh ]] && cp fgmod.sh "$mod_path/fgmod" || exit 1
    [[ -f fgmod-uninstaller.sh ]] && cp fgmod-uninstaller.sh "$mod_path" || exit 1
fi
cd "$mod_path" || exit 1

curl -OLf https://github.com/artur-graniszewski/DLSS-Enabler/releases/download/$enablerver/dlss-enabler-setup-$enablerver.exe || exit 1
curl -OLf https://download.nvidia.com/XFree86/Linux-x86_64/$nvidiaver/NVIDIA-Linux-x86_64-$nvidiaver.run || exit 1
curl -OLf https://raw.githubusercontent.com/mozilla/fxc2/master/dll/d3dcompiler_47.dll || exit 1
curl -OLf https://github.com/FakeMichau/innoextract/releases/download/6.3.0/innoextract || exit 1
curl -OLf https://github.com/FakeMichau/fakenvapi/releases/download/$fakenvapiver/fakenvapi.7z || exit 1
[[ $standalone -eq 0 ]] && curl -o fgmod -Lf https://raw.githubusercontent.com/FakeMichau/fgmod/main/fgmod.sh
[[ $standalone -eq 0 ]] && curl -OL https://raw.githubusercontent.com/FakeMichau/fgmod/main/fgmod-uninstaller.sh

[[ ! -f dlss-enabler-setup-$enablerver.exe ]] || 
[[ ! -f NVIDIA-Linux-x86_64-$nvidiaver.run ]] || 
[[ ! -f d3dcompiler_47.dll ]] || 
[[ ! -f innoextract ]] || 
[[ ! -f fakenvapi.7z ]] || 
[[ ! -f fgmod ]] || 
[[ ! -f fgmod-uninstaller.sh ]] && exit 1

# Extract files
chmod +x NVIDIA-Linux-x86_64-$nvidiaver.run
./NVIDIA-Linux-x86_64-$nvidiaver.run -x

chmod +x innoextract
./innoextract dlss-enabler-setup-$enablerver.exe

# Prepare mod files
mv app/* .
rm -r app
[[ -f "$(which 7z 2>/dev/null)" ]] && 7z -y x fakenvapi.7z
cp -f NVIDIA-Linux-x86_64-$nvidiaver/nvngx.dll _nvngx.dll
cp -f NVIDIA-Linux-x86_64-$nvidiaver/LICENSE "licenses/LICENSE (NVIDIA driver)"
chmod +r _nvngx.dll
rm -rf innoextract NVIDIA-Linux-x86_64-$nvidiaver dlss-enabler-setup-$enablerver.exe NVIDIA-Linux-x86_64-$nvidiaver.run fakenvapi.7z
rm -rf plugins nvapi64-proxy.dll dlss-enabler-fsr.dll dlss-enabler-xess.dll dbghelp.dll version.dll winmm.dll nvngx.dll dlss-finder.exe dlss-enabler.log dlssg_to_fsr3.log fakenvapi.log "LICENSE (DLSSG to FSR3 mod).txt" "Readme (DLSS enabler).txt" "READ ME (DLSSG to FSR3 mod).txt" "XESS LICENSE.pdf"
[[ -f "$(which nvidia-smi 2>/dev/null)" ]] && rm -rf nvapi64.dll fakenvapi.ini

sed -i 's|mod_path="/usr/share/fgmod"|mod_path="'"$mod_path"'"|g' fgmod
chmod +x fgmod

sed -i 's|mod_path="/usr/share/fgmod"|mod_path="'"$mod_path"'"|g' fgmod-uninstaller.sh
chmod +x fgmod-uninstaller.sh

echo ""

# Flatpak doesn't have access to home by default
if flatpak list | grep "com.valvesoftware.Steam" 1>/dev/null; then
    echo Flatpak version of Steam detected, adding access to fgmod\'s folder
    echo Please restart Steam!
    flatpak override --user --filesystem="$mod_path" com.valvesoftware.Steam
fi

echo For Steam, add this to the launch options: "$mod_path/fgmod" %COMMAND%
echo For Heroic, add this as a new wrapper: "$mod_path/fgmod"
echo All done!
#!/usr/bin/env bash

set -euo pipefail
set -x
exec > >(tee -i /tmp/fgmod-prefix-managed.log) 2>&1

log() {
  echo "$*"
  logger -t fgmod-prefix-managed "$*"
}

error_exit() {
  local message="$1"
  echo "❌ $message"
  logger -t fgmod-prefix-managed "ERROR: $message"
  if [[ -n "${STEAM_ZENITY:-}" ]]; then
    "$STEAM_ZENITY" --error --text "$message" || true
  elif command -v zenity >/dev/null 2>&1; then
    zenity --error --text "$message" || true
  fi
  exit 1
}

bundle_root="${HOME}/fgmod"
managed_dir_name="optiscaler-managed"
manifest_name="manifest.env"
default_proxy="winmm"
proxy_name="${OPTISCALER_PROXY:-${DLL:-}}"
proxy_name="${proxy_name%.dll}"
proxy_dll=""
backup_dll=""

support_files=(
  "libxess.dll"
  "libxess_dx11.dll"
  "libxess_fg.dll"
  "libxell.dll"
  "amd_fidelityfx_dx12.dll"
  "amd_fidelityfx_framegeneration_dx12.dll"
  "amd_fidelityfx_upscaler_dx12.dll"
  "amd_fidelityfx_vk.dll"
  "nvngx.dll"
  "dlssg_to_fsr3_amd_is_better.dll"
  "fakenvapi.dll"
  "fakenvapi.ini"
)

[[ -d "$bundle_root" ]] || error_exit "OptiScaler runtime not installed at $bundle_root"
[[ -n "${STEAM_COMPAT_DATA_PATH:-}" ]] || error_exit "STEAM_COMPAT_DATA_PATH is required. Use this wrapper from a Steam/Proton launch option."
[[ $# -ge 1 ]] || error_exit "Usage: $0 program [program_arguments...]"

compatdata_path="$STEAM_COMPAT_DATA_PATH"
system32_path="$compatdata_path/pfx/drive_c/windows/system32"
managed_root="$compatdata_path/$managed_dir_name"
manifest_path="$managed_root/$manifest_name"
managed_ini="$managed_root/OptiScaler.ini"
managed_plugins="$managed_root/plugins"

cleanup_proxy_stage() {
  local cleanup_proxy="$1"
  local cleanup_proxy_dll="${cleanup_proxy}.dll"
  local cleanup_backup_dll="${cleanup_proxy}-original.dll"

  rm -f "$system32_path/$cleanup_proxy_dll"
  if [[ -f "$system32_path/$cleanup_backup_dll" ]]; then
    mv -f "$system32_path/$cleanup_backup_dll" "$system32_path/$cleanup_proxy_dll"
  fi
}

cleanup_stage_files() {
  local cleanup_proxy="$1"
  rm -f "$system32_path/OptiScaler.ini"
  for file_name in "${support_files[@]}"; do
    rm -f "$system32_path/$file_name"
  done
  rm -f "$system32_path/OptiScaler.log"
  rm -rf "$system32_path/plugins"
  cleanup_proxy_stage "$cleanup_proxy"
}

mkdir -p "$system32_path" "$managed_root" "$managed_plugins"

existing_proxy=""
preferred_proxy=""
if [[ -f "$manifest_path" ]]; then
  # shellcheck disable=SC1090
  source "$manifest_path"
  existing_proxy="${MANAGED_PROXY:-}"
  preferred_proxy="${PREFERRED_PROXY:-}"
fi

if [[ -z "$proxy_name" ]]; then
  proxy_name="${preferred_proxy:-$default_proxy}"
fi

case "$proxy_name" in
  winmm|dxgi|version|dbghelp|winhttp|wininet|d3d12) ;;
  *) error_exit "Unsupported OPTISCALER_PROXY '$proxy_name'." ;;
esac

proxy_dll="${proxy_name}.dll"
backup_dll="${proxy_name}-original.dll"

if [[ -n "$existing_proxy" && "$existing_proxy" != "$proxy_name" ]]; then
  log "Switching managed proxy from $existing_proxy to $proxy_name"
  cleanup_stage_files "$existing_proxy"
fi

[[ -f "$bundle_root/OptiScaler.ini" ]] || error_exit "Missing OptiScaler.ini in runtime bundle"
[[ -f "$bundle_root/update-optiscaler-config.py" ]] || error_exit "Missing update-optiscaler-config.py in runtime bundle"

python_bin="python3"
if ! command -v "$python_bin" >/dev/null 2>&1; then
  python_bin="python"
fi
command -v "$python_bin" >/dev/null 2>&1 || error_exit "Python interpreter not found"

if [[ ! -f "$managed_ini" ]]; then
  cp -f "$bundle_root/OptiScaler.ini" "$managed_ini"
fi

"$python_bin" "$bundle_root/update-optiscaler-config.py" "$managed_ini"
sed -i 's/^UseHQFont[[:space:]]*=[[:space:]]*auto$/UseHQFont=false/' "$managed_ini" || true

if [[ -d "$bundle_root/plugins" ]]; then
  rm -rf "$managed_plugins"
  mkdir -p "$managed_plugins"
  cp -f "$bundle_root/plugins"/* "$managed_plugins/" 2>/dev/null || true
fi

for file_name in "${support_files[@]}"; do
  if [[ -f "$bundle_root/$file_name" ]]; then
    cp -f "$bundle_root/$file_name" "$system32_path/$file_name"
  fi
done

if [[ -d "$managed_plugins" ]]; then
  rm -rf "$system32_path/plugins"
  mkdir -p "$system32_path/plugins"
  cp -f "$managed_plugins"/* "$system32_path/plugins/" 2>/dev/null || true
fi

if [[ -f "$system32_path/$proxy_dll" && ! -f "$system32_path/$backup_dll" ]]; then
  mv -f "$system32_path/$proxy_dll" "$system32_path/$backup_dll"
fi

if [[ -f "$bundle_root/renames/$proxy_dll" ]]; then
  cp -f "$bundle_root/renames/$proxy_dll" "$system32_path/$proxy_dll"
else
  cp -f "$bundle_root/OptiScaler.dll" "$system32_path/$proxy_dll"
fi

cp -f "$managed_ini" "$system32_path/OptiScaler.ini"

runtime_version="unknown"
if [[ -f "$bundle_root/version.txt" ]]; then
  runtime_version="$(<"$bundle_root/version.txt")"
fi

cat > "$manifest_path" <<EOF
MANAGED_PROXY="$proxy_name"
PREFERRED_PROXY="$preferred_proxy"
BUNDLE_ROOT="$bundle_root"
BUNDLE_VERSION="$runtime_version"
SYSTEM32_PATH="$system32_path"
EOF

export SteamDeck=0
if [[ -n "${WINEDLLOVERRIDES:-}" ]]; then
  export WINEDLLOVERRIDES="${WINEDLLOVERRIDES},${proxy_name}=n,b"
else
  export WINEDLLOVERRIDES="${proxy_name}=n,b"
fi

while [[ $# -gt 0 && "$1" == "--" ]]; do
  shift
done

log "Using compatdata path: $compatdata_path"
log "Using system32 path: $system32_path"
log "Using prefix-managed proxy: $proxy_dll"
log "Using WINEDLLOVERRIDES=$WINEDLLOVERRIDES"

set +e
"$@"
exit_code=$?
set -e

if [[ -f "$system32_path/OptiScaler.ini" ]]; then
  cp -f "$system32_path/OptiScaler.ini" "$managed_ini"
fi

exit "$exit_code"

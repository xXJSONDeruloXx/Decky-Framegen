#!/usr/bin/env bash

set -euo pipefail
set -x
exec > >(tee -i /tmp/fgmod-prefix-cleanup.log) 2>&1

log() {
  echo "$*"
  logger -t fgmod-prefix-cleanup "$*"
}

error_exit() {
  local message="$1"
  echo "❌ $message"
  logger -t fgmod-prefix-cleanup "ERROR: $message"
  if [[ -n "${STEAM_ZENITY:-}" ]]; then
    "$STEAM_ZENITY" --error --text "$message" || true
  elif command -v zenity >/dev/null 2>&1; then
    zenity --error --text "$message" || true
  fi
  exit 1
}

managed_dir_name="optiscaler-managed"
manifest_name="manifest.env"
default_proxy="${OPTISCALER_PROXY:-${DLL:-winmm}}"
default_proxy="${default_proxy%.dll}"

support_files=(
  "OptiScaler.ini"
  "OptiScaler.log"
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
  "dlssg_to_fsr3.ini"
  "dlssg_to_fsr3.log"
  "nvapi64.dll"
  "nvapi64.dll.b"
  "fakenvapi.log"
  "dlss-enabler.dll"
  "dlss-enabler-upscaler.dll"
  "dlss-enabler.log"
  "nvngx-wrapper.dll"
  "_nvngx.dll"
  "dlssg_to_fsr3_amd_is_better-3.0.dll"
  "OptiScaler.asi"
)

[[ -n "${STEAM_COMPAT_DATA_PATH:-}" ]] || error_exit "STEAM_COMPAT_DATA_PATH is required. Use this wrapper from a Steam/Proton launch option."
[[ $# -ge 1 ]] || error_exit "Usage: $0 program [program_arguments...]"

compatdata_path="$STEAM_COMPAT_DATA_PATH"
system32_path="$compatdata_path/pfx/drive_c/windows/system32"
managed_root="$compatdata_path/$managed_dir_name"
manifest_path="$managed_root/$manifest_name"
proxy_name="$default_proxy"

if [[ -f "$manifest_path" ]]; then
  # shellcheck disable=SC1090
  source "$manifest_path"
  proxy_name="${MANAGED_PROXY:-$proxy_name}"
fi

proxy_dll="${proxy_name}.dll"
backup_dll="${proxy_name}-original.dll"

for file_name in "${support_files[@]}"; do
  rm -f "$system32_path/$file_name"
done

rm -rf "$system32_path/plugins"
rm -f "$system32_path/$proxy_dll"

if [[ -f "$system32_path/$backup_dll" ]]; then
  mv -f "$system32_path/$backup_dll" "$system32_path/$proxy_dll"
fi

rm -rf "$managed_root"

log "Cleaned prefix-managed OptiScaler files from $compatdata_path using proxy $proxy_name"

while [[ $# -gt 0 && "$1" == "--" ]]; do
  shift
done

set +e
"$@"
exit_code=$?
set -e

exit "$exit_code"

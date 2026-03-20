#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}")" &> /dev/null && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." &> /dev/null && pwd)"
LOCAL_CLI="$REPO_ROOT/cli/decky"
SYSTEM_CLI="$(command -v decky || true)"

if [[ -x "$LOCAL_CLI" ]]; then
  CLI_LOCATION="$LOCAL_CLI"
elif [[ -n "$SYSTEM_CLI" ]]; then
  CLI_LOCATION="$SYSTEM_CLI"
else
  echo "Decky CLI not found. Run .vscode/setup.sh first or install the decky CLI manually."
  exit 1
fi

echo "Building plugin in $REPO_ROOT"
echo "Using Decky CLI: $CLI_LOCATION"

if [[ "${DECKY_BUILD_USE_SUDO:-0}" == "1" ]]; then
  sudo -E "$CLI_LOCATION" plugin build "$REPO_ROOT"
else
  "$CLI_LOCATION" plugin build "$REPO_ROOT"
fi

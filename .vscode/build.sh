#!/usr/bin/env bash
CLI_LOCATION="$(pwd)/cli"
echo "Building plugin in $(pwd)"
print(f"Please input sudo password to proceed.\n")

# read -s sudopass

# printf "\n"

echo $sudopass | sudo -E $CLI_LOCATION/decky plugin build $(pwd)

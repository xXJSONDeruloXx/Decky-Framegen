#!/usr/bin/env bash

set -x  # Enable debugging
exec > >(tee -i /tmp/prepare.log) 2>&1  # Log output and errors

# Remove ~/fgmod directory if it exists
if [[ -d "$HOME/fgmod" ]]; then
    rm -rf "$HOME/fgmod"
fi

echo "FGmod removed"
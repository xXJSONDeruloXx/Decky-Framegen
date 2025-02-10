#!/usr/bin/env bash

# Remove ~/fgmod-plus directory if it exists
if [[ -d "$HOME/fgmod-plus" ]]; then
    rm -rf "$HOME/fgmod-plus"
fi

echo "FGmod-plus removed"
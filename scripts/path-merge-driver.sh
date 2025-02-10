#!/bin/bash

# Get file versions from git merge
BASE=$1
CURRENT=$2
OTHER=$3

# Perform normal merge first
git merge-file -p "$CURRENT" "$BASE" "$OTHER" > temp_merge

# Ensure our specific paths are preserved
sed -i '' 's|/fgmod/|/fgmod-plus/|g' temp_merge
sed -i '' 's|"name": "decky-framegen"|"name": "decky-framegen-plus"|g' temp_merge
sed -i '' 's|"name": "Decky-Framegen"|"name": "Decky-Framegen-Plus"|g' temp_merge
sed -i '' 's|binaries-DLSS-Enabler-3.02-Stable|binaries-DLSS-Enabler-3.03-Trunk|g' temp_merge

cat temp_merge > "$CURRENT"
rm temp_merge
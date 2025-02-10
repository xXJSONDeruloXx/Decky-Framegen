#!/bin/bash

# Get file versions from git merge
BASE=$1
CURRENT=$2
OTHER=$3

# Perform normal merge first
git merge-file -p "$CURRENT" "$BASE" "$OTHER" > temp_merge

# Ensure our specific paths are preserved
# File paths
sed -i '' 's|/fgmod/|/fgmod-plus/|g' temp_merge
sed -i '' 's|"$HOME/fgmod"|"$HOME/fgmod-plus"|g' temp_merge
sed -i '' 's|/usr/share/fgmod|/usr/share/fgmod-plus|g' temp_merge

# Plugin naming
sed -i '' 's|"name": "decky-framegen"|"name": "decky-framegen-plus"|g' temp_merge
sed -i '' 's|"name": "Decky-Framegen"|"name": "Decky-Framegen-Plus"|g' temp_merge
sed -i '' 's|"Install FG Mod"|"Install FG Mod Plus"|g' temp_merge
sed -i '' 's|"Uninstall FG Mod"|"Uninstall FG Mod Plus"|g' temp_merge
sed -i '' 's|titleView: <div>Decky Framegen</div>|titleView: <div>Decky FG Plus</div>|g' temp_merge
sed -i '' 's|"FGmod removed"|"FGmod-plus removed"|g' temp_merge

# Binary versions
sed -i '' 's|binaries-DLSS-Enabler-3.02-Stable|binaries-DLSS-Enabler-3.03-Trunk|g' temp_merge

# Remote binary bundling flag
sed -i '' 's|"remote_binary_bundling" : false|"remote_binary_bundling" : true|g' temp_merge

cat temp_merge > "$CURRENT"
rm temp_merge
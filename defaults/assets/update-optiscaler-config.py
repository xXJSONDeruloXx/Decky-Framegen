import os
import sys
import re
from configparser import ConfigParser

def update_optiscaler_config(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    with open(file_path, 'r') as f:
        lines = f.readlines()

    config = ConfigParser()
    config.optionxform = str  # Preserve case for keys (otherwise PATH could match Path)
    config.read(file_path)

    # Because we want to support unprefixed env variables, we need to count key occurrences across all sections of the ini file
    # Keys that appear multiple times should be prefixed like Section_Key by the user for them to be targeted properly

    key_occurrences = {}
    key_to_sections = {}
    for section in config.sections():
        for key in config.options(section):
            key_occurrences[key] = key_occurrences.get(key, 0) + 1
            if key not in key_to_sections:
                key_to_sections[key] = []
            key_to_sections[key].append(section)

    env_updates = []

    # Handle OptiScaler_Section_Key format
    optiscaler_vars = {k: v for k, v in os.environ.items() if k.startswith("OptiScaler_")}
    for env_name, env_value in optiscaler_vars.items():
        parts = env_name.split('_', 2)
        if len(parts) >= 3:
            env_updates.append(('optiscaler', parts[1], parts[2], env_value, env_name))

    # Handle Section_Key and Key formats
    other_vars = {k: v for k, v in os.environ.items() if not k.startswith("OptiScaler_")}
    for env_name, env_value in other_vars.items():
        # Try Section_Key format
        if '_' in env_name:
            parts = env_name.split('_', 1)
            section = parts[0]
            key = parts[1]
            # Check if this section exists and has this key
            if config.has_section(section) and config.has_option(section, key):
                env_updates.append(('section_key', section, key, env_value, env_name))
                continue

        # Try Key format (only if key appears exactly once across all sections)
        if env_name in key_occurrences and key_occurrences[env_name] == 1:
            section = key_to_sections[env_name][0]
            env_updates.append(('key', section, env_name, env_value, env_name))

    print(f"Found {len(env_updates)} updates to apply")
    for entry in env_updates:
        print(f"> {entry}")

    for update_type, section_target, key_target, env_value, env_name in env_updates:
        found_section = False

        # Regex to match [Section] and Key=Value (case-sensitive)
        section_pattern = re.compile(rf'^\s*\[{re.escape(section_target)}]\s*')
        key_pattern = re.compile(rf'^(\s*{re.escape(key_target)}\s*)=.*')

        for i, line in enumerate(lines):
            # Track if we are inside the correct section
            if section_pattern.match(line):
                found_section = True
                continue

            # If we hit a new section before finding the key, the key doesn't exist in the target section
            if found_section and line.strip().startswith('[') and not section_pattern.match(line):
                break

            # Replace the value if the key is found within the correct section
            if found_section and key_pattern.match(line):
                lines[i] = key_pattern.sub(r'\1=' + env_value, line)
                print(f"Updated: [{section_target}] {key_target} = {env_value} (from {env_name})")
                break

    # Write the modified content back
    with open(file_path, 'w') as f:
        f.writelines(lines)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update-optiscaler-config.py <path_to_ini>")
    else:
        update_optiscaler_config(sys.argv[1])
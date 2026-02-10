import os
import sys
import re

def update_optiscaler_config(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Get environment variables starting with OptiScaler_
    env_vars = {k: v for k, v in os.environ.items() if k.startswith("OptiScaler_")}

    for env_name, env_value in env_vars.items():
        # Split OptiScaler_Section_Key
        parts = env_name.split('_', 2)
        if len(parts) < 3:
            continue

        section_target = parts[1]
        key_target = parts[2]

        found_section = False

        # Regex to match [Section] and Key=Value
        section_pattern = re.compile(rf'^\s*\[{re.escape(section_target)}\]\s*')
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
                print(f"Updated: [{section_target}] {key_target} = {env_value}")
                break

    # Write the modified content back
    with open(file_path, 'w') as f:
        f.writelines(lines)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update-optiscaler-config.py <path_to_ini>")
    else:
        update_optiscaler_config(sys.argv[1])
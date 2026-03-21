import decky
import os
import re
import shutil
import subprocess
from configparser import ConfigParser
from pathlib import Path

# Toggle to enable overwriting the upscaler DLL from the static remote binary.
UPSCALER_OVERWRITE_ENABLED = True

BUNDLE_DIRNAME = "fgmod"
MANAGED_DIRNAME = "optiscaler-managed"
MANIFEST_FILENAME = "manifest.env"

SUPPORTED_PROXIES = [
    "dxgi",
    "winmm",
    "dbghelp",
    "version",
    "wininet",
    "winhttp",
    "d3d12",
]

SUPPORT_FILES = [
    "libxess.dll",
    "libxess_dx11.dll",
    "libxess_fg.dll",
    "libxell.dll",
    "amd_fidelityfx_dx12.dll",
    "amd_fidelityfx_framegeneration_dx12.dll",
    "amd_fidelityfx_upscaler_dx12.dll",
    "amd_fidelityfx_vk.dll",
    "nvngx.dll",
    "dlssg_to_fsr3_amd_is_better.dll",
    "fakenvapi.dll",
    "fakenvapi.ini",
]

REQUIRED_BUNDLE_FILES = [
    "OptiScaler.dll",
    "OptiScaler.ini",
    *SUPPORT_FILES,
    "fgmod",
    "fgmod-uninstaller.sh",
    "update-optiscaler-config.py",
]

LEGACY_FILES = [
    "dlssg_to_fsr3.ini",
    "dlssg_to_fsr3.log",
    "nvapi64.dll",
    "nvapi64.dll.b",
    "fakenvapi.log",
    "dlss-enabler.dll",
    "dlss-enabler-upscaler.dll",
    "dlss-enabler.log",
    "nvngx-wrapper.dll",
    "_nvngx.dll",
    "dlssg_to_fsr3_amd_is_better-3.0.dll",
    "OptiScaler.asi",
    "OptiScaler.log",
]



class Plugin:
    async def _main(self):
        decky.logger.info("Framegen plugin loaded")

    async def _unload(self):
        decky.logger.info("Framegen plugin unloaded.")

    def _home_path(self) -> Path:
        try:
            return Path(decky.HOME)
        except TypeError:
            return Path(str(decky.HOME))

    def _bundle_path(self) -> Path:
        return self._home_path() / BUNDLE_DIRNAME

    def _steam_root_candidates(self) -> list[Path]:
        home = self._home_path()
        candidates = [
            home / ".local" / "share" / "Steam",
            home / ".steam" / "steam",
        ]

        unique = []
        seen = set()
        for candidate in candidates:
            key = str(candidate)
            if key not in seen:
                unique.append(candidate)
                seen.add(key)
        return unique

    def _steam_library_paths(self) -> list[Path]:
        library_paths: list[Path] = []
        seen = set()

        for steam_root in self._steam_root_candidates():
            if steam_root.exists():
                key = str(steam_root)
                if key not in seen:
                    library_paths.append(steam_root)
                    seen.add(key)

            library_file = steam_root / "steamapps" / "libraryfolders.vdf"
            if not library_file.exists():
                continue

            try:
                with open(library_file, "r", encoding="utf-8", errors="replace") as file:
                    for line in file:
                        if '"path"' not in line:
                            continue
                        path = line.split('"path"', 1)[1].strip().strip('"').replace("\\\\", "/")
                        candidate = Path(path)
                        key = str(candidate)
                        if key not in seen:
                            library_paths.append(candidate)
                            seen.add(key)
            except Exception as exc:
                decky.logger.error(f"Failed to parse {library_file}: {exc}")

        return library_paths

    def _compatdata_dirs_for_appid(self, appid: str) -> list[Path]:
        matches = []
        for library in self._steam_library_paths():
            compatdata_dir = library / "steamapps" / "compatdata" / str(appid)
            if compatdata_dir.exists():
                matches.append(compatdata_dir)
        return matches

    def _parse_manifest_env(self, manifest_path: Path) -> dict:
        data = {}
        if not manifest_path.exists():
            return data

        try:
            with open(manifest_path, "r", encoding="utf-8", errors="replace") as manifest:
                for raw_line in manifest:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    data[key.strip()] = value.strip().strip('"')
        except Exception as exc:
            decky.logger.error(f"Failed to parse manifest {manifest_path}: {exc}")

        return data

    def _write_manifest_env(self, manifest_path: Path, updates: dict) -> dict:
        data = self._parse_manifest_env(manifest_path)
        for key, value in updates.items():
            if value is None:
                continue
            data[str(key)] = str(value)

        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as manifest:
            for key in sorted(data.keys()):
                manifest.write(f'{key}="{data[key]}"\n')
        return data

    def _normalize_proxy(self, proxy: str | None) -> str:
        normalized = (proxy or "winmm").replace(".dll", "").strip().lower()
        if normalized not in SUPPORTED_PROXIES:
            raise ValueError(f"Unsupported proxy '{proxy}'")
        return normalized

    def _find_installed_game(self, appid: str | None = None) -> list[dict]:
        games = []
        for library_path in self._steam_library_paths():
            steamapps_path = library_path / "steamapps"
            if not steamapps_path.exists():
                continue

            for appmanifest in steamapps_path.glob("appmanifest_*.acf"):
                game_info = {"appid": "", "name": "", "library_path": str(library_path)}
                try:
                    with open(appmanifest, "r", encoding="utf-8", errors="replace") as file:
                        for line in file:
                            if '"appid"' in line:
                                game_info["appid"] = line.split('"appid"', 1)[1].strip().strip('"')
                            if '"name"' in line:
                                game_info["name"] = line.split('"name"', 1)[1].strip().strip('"')
                except Exception as exc:
                    decky.logger.error(f"Skipping {appmanifest}: {exc}")

                if not game_info["appid"] or not game_info["name"]:
                    continue
                if "Proton" in game_info["name"] or "Steam Linux Runtime" in game_info["name"]:
                    continue
                if appid is None or str(game_info["appid"]) == str(appid):
                    games.append(game_info)

        deduped = {}
        for game in games:
            deduped[str(game["appid"])] = game
        return list(deduped.values())

    def _compatdata_dir_for_appid(self, appid: str, create: bool = False) -> Path | None:
        compatdata_dirs = self._compatdata_dirs_for_appid(str(appid))
        if compatdata_dirs:
            return compatdata_dirs[0]

        if not create:
            return None

        installed_games = self._find_installed_game(appid)
        if not installed_games:
            return None

        library_path = Path(installed_games[0]["library_path"])
        compatdata_dir = library_path / "steamapps" / "compatdata" / str(appid)
        compatdata_dir.mkdir(parents=True, exist_ok=True)
        return compatdata_dir

    def _managed_paths_for_appid(self, appid: str, create: bool = False) -> dict | None:
        compatdata_dir = self._compatdata_dir_for_appid(str(appid), create=create)
        if not compatdata_dir:
            return None

        managed_root = compatdata_dir / MANAGED_DIRNAME
        system32 = compatdata_dir / "pfx" / "drive_c" / "windows" / "system32"
        if create:
            managed_root.mkdir(parents=True, exist_ok=True)

        return {
            "compatdata_dir": compatdata_dir,
            "managed_root": managed_root,
            "manifest_path": managed_root / MANIFEST_FILENAME,
            "managed_ini": managed_root / "OptiScaler.ini",
            "system32": system32,
            "live_ini": system32 / "OptiScaler.ini",
        }

    def _ensure_managed_ini(self, appid: str) -> dict:
        paths = self._managed_paths_for_appid(appid, create=True)
        if not paths:
            raise FileNotFoundError(f"Unable to resolve compatdata path for app {appid}")

        managed_ini = paths["managed_ini"]
        if managed_ini.exists():
            return paths

        bundle_ini = self._bundle_path() / "OptiScaler.ini"
        if not bundle_ini.exists():
            raise FileNotFoundError("OptiScaler runtime is not installed; missing bundled OptiScaler.ini")

        shutil.copy2(bundle_ini, managed_ini)
        self._modify_optiscaler_ini(managed_ini)
        return paths

    def _read_ini_config(self, ini_path: Path) -> ConfigParser:
        config = ConfigParser(interpolation=None)
        config.optionxform = str
        if ini_path.exists():
            config.read(ini_path, encoding="utf-8")
        return config

    def _bundle_ini_path(self) -> Path:
        return self._bundle_path() / "OptiScaler.ini"

    def _find_sections_for_key(self, config: ConfigParser, key: str) -> list[str]:
        return [section for section in config.sections() if config.has_option(section, key)]

    def _setting_id(self, section: str, key: str) -> str:
        return f"{section}.{key}"

    def _humanize_key(self, value: str) -> str:
        text = value.replace("_", " ")
        text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _sanitize_default_value(self, value: str) -> str:
        candidate = value.strip()
        if " - " in candidate and re.match(r"^[^ ]+\s+-\s+", candidate):
            candidate = candidate.split(" - ", 1)[0].strip()
        if "," in candidate and re.match(r"^[^,]+,", candidate):
            candidate = candidate.split(",", 1)[0].strip()
        return candidate

    def _extract_default_from_comments(self, comment_lines: list[str]) -> str | None:
        for line in comment_lines:
            match = re.search(r"Default\s*\(auto\)\s*is\s*([^;]+)", line, flags=re.IGNORECASE)
            if match:
                return self._sanitize_default_value(match.group(1))
        return None

    def _extract_enum_options(self, comment_lines: list[str], current_value: str) -> list[dict]:
        options = []
        seen = set()

        def add_option(value: str, label: str | None = None):
            normalized = value.strip()
            if not normalized or normalized in seen:
                return
            seen.add(normalized)
            options.append({"value": normalized, "label": label or normalized})

        if current_value == "auto":
            add_option("auto")

        for line in comment_lines:
            clean_line = line.strip()
            lower_line = clean_line.lower()

            if "true or false" in lower_line:
                add_option("auto")
                add_option("true")
                add_option("false")
                continue

            if "|" in clean_line and "=" in clean_line:
                for piece in clean_line.split("|"):
                    match = re.match(r"\s*([^=|]+?)\s*=\s*(.+)\s*$", piece)
                    if match:
                        value = match.group(1).strip()
                        label = f"{value} - {match.group(2).strip()}"
                        add_option(value, label)
                continue

            before_default = clean_line.split("- Default", 1)[0].strip()
            if "," in before_default:
                for item in before_default.split(","):
                    normalized = re.sub(r"\s*\(.*?\)", "", item).strip()
                    if normalized and len(normalized) < 64 and "=" not in normalized:
                        add_option(normalized)

        if current_value and current_value not in seen:
            add_option(current_value)

        return options

    def _extract_numeric_range(self, comment_lines: list[str]) -> tuple[float | None, float | None]:
        patterns = [
            r"\bFrom\s+(-?\d+(?:\.\d+)?)\s+to\s+(-?\d+(?:\.\d+)?)\b",
            r"\b(-?\d+(?:\.\d+)?)\s+to\s+(-?\d+(?:\.\d+)?)\b",
            r"\b(-?\d+(?:\.\d+)?)\s+-\s+(-?\d+(?:\.\d+)?)\b",
        ]

        for line in comment_lines:
            if "=" in line and "|" in line:
                continue
            for pattern in patterns:
                match = re.search(pattern, line, flags=re.IGNORECASE)
                if match:
                    return float(match.group(1)), float(match.group(2))
        return None, None

    def _infer_setting_metadata(self, section: str, key: str, current_value: str, comment_lines: list[str]) -> dict:
        description_lines = [line for line in comment_lines if line and set(line) != {"-"}]
        description = "\n".join(description_lines)
        default_value = self._extract_default_from_comments(description_lines)
        enum_options = self._extract_enum_options(description_lines, current_value)
        range_min, range_max = self._extract_numeric_range(description_lines)
        description_lower = description.lower()

        numeric_type = "float" if any(token in description_lower for token in ["float", ".0", "timer resolution"]) else "int"
        is_numeric = any(token in description_lower for token in ["float", "integer value", "uint", "int ", "0x", "measured in timer resolution units"]) or (
            range_min is not None and range_max is not None
        )
        is_path = "path" in key.lower() or " path" in description_lower or "folder" in description_lower
        is_keycode = "shortcut key" in description_lower or "virtual-key-codes" in description_lower or "0x" in description_lower

        control = "text"
        if enum_options and len(enum_options) > 1:
            control = "dropdown"
        elif range_min is not None and range_max is not None and not is_path and not is_keycode and (range_max - range_min) <= 1000:
            control = "range"
        elif is_numeric and not is_path:
            control = "number"

        step = 1
        if control == "range":
            if numeric_type == "float" or (range_min is not None and (not float(range_min).is_integer() or not float(range_max).is_integer())):
                step = 0.01
                if (range_max - range_min) > 10:
                    step = 0.1
            else:
                step = 1

        return {
            "id": self._setting_id(section, key),
            "section": section,
            "key": key,
            "label": self._humanize_key(key),
            "description": description,
            "default": default_value or current_value,
            "control": control,
            "options": enum_options,
            "rangeMin": range_min,
            "rangeMax": range_max,
            "step": step,
            "numericType": numeric_type,
            "isPath": is_path,
            "isKeycode": is_keycode,
        }

    def _parse_ini_schema(self, template_ini_path: Path) -> list[dict]:
        if not template_ini_path.exists():
            raise FileNotFoundError(f"Template ini not found at {template_ini_path}")

        sections = []
        current_section = None
        section_entry = None
        comment_buffer: list[str] = []

        with open(template_ini_path, "r", encoding="utf-8", errors="replace") as ini_file:
            for raw_line in ini_file:
                stripped = raw_line.strip()
                if not stripped:
                    continue

                if stripped.startswith(";"):
                    cleaned = stripped.lstrip(";").strip()
                    if cleaned:
                        comment_buffer.append(cleaned)
                    continue

                section_match = re.match(r"^\[(.+)]$", stripped)
                if section_match:
                    current_section = section_match.group(1).strip()
                    section_entry = {"id": current_section, "label": current_section, "settings": []}
                    sections.append(section_entry)
                    comment_buffer = []
                    continue

                if current_section and "=" in stripped and not stripped.startswith("#"):
                    key, value = stripped.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    metadata = self._infer_setting_metadata(current_section, key, value, comment_buffer)
                    section_entry["settings"].append(metadata)
                    comment_buffer = []

        return sections

    def _extract_all_settings(self, ini_path: Path, schema_sections: list[dict]) -> dict:
        config = self._read_ini_config(ini_path)
        values = {}
        for section in schema_sections:
            section_name = section["id"]
            for setting in section["settings"]:
                value = setting["default"]
                if config.has_option(section_name, setting["key"]):
                    value = config.get(section_name, setting["key"])
                values[setting["id"]] = value
        return values

    def _schema_lookup(self, schema_sections: list[dict]) -> dict:
        lookup = {}
        for section in schema_sections:
            for setting in section["settings"]:
                lookup[setting["id"]] = setting
        return lookup

    def _replace_ini_values(self, ini_path: Path, resolved_updates: list[tuple[str, str, str]]) -> None:
        lines = []
        if ini_path.exists():
            with open(ini_path, "r", encoding="utf-8", errors="replace") as ini_file:
                lines = ini_file.readlines()

        for section, key, value in resolved_updates:
            section_pattern = re.compile(rf"^\s*\[{re.escape(section)}]\s*$")
            any_section_pattern = re.compile(r"^\s*\[.*]\s*$")
            key_pattern = re.compile(rf"^\s*{re.escape(key)}\s*=.*$")

            in_target_section = False
            section_found = False
            inserted_or_updated = False
            insert_index = len(lines)

            for index, line in enumerate(lines):
                if section_pattern.match(line):
                    in_target_section = True
                    section_found = True
                    insert_index = index + 1
                    continue

                if in_target_section and any_section_pattern.match(line):
                    insert_index = index
                    break

                if in_target_section:
                    if key_pattern.match(line):
                        newline = "\n" if line.endswith("\n") else ""
                        lines[index] = f"{key}={value}{newline}"
                        inserted_or_updated = True
                        break
                    insert_index = index + 1

            if inserted_or_updated:
                continue

            if not section_found:
                if lines and lines[-1].strip():
                    lines.append("\n")
                lines.append(f"[{section}]\n")
                lines.append(f"{key}={value}\n")
                continue

            lines[insert_index:insert_index] = [f"{key}={value}\n"]

        with open(ini_path, "w", encoding="utf-8") as ini_file:
            ini_file.writelines(lines)

    def _disable_hq_font_auto(self, ini_file: Path) -> bool:
        try:
            if not ini_file.exists():
                decky.logger.warning(f"OptiScaler.ini not found at {ini_file}")
                return False

            with open(ini_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            updated_content = re.sub(r"UseHQFont\s*=\s*auto", "UseHQFont=false", content)
            if updated_content != content:
                with open(ini_file, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                decky.logger.info("Set UseHQFont=false to avoid missing font assertions")

            return True
        except Exception as exc:
            decky.logger.error(f"Failed to update HQ font setting in OptiScaler.ini: {exc}")
            return False

    def _modify_optiscaler_ini(self, ini_file: Path) -> bool:
        """Modify OptiScaler.ini to set FG defaults, ASI plugin settings, and safe font defaults."""
        try:
            if not ini_file.exists():
                decky.logger.warning(f"OptiScaler.ini not found at {ini_file}")
                return False

            with open(ini_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            updated_content = re.sub(r"FGType\s*=\s*auto", "FGType=nukems", content)
            updated_content = re.sub(r"Fsr4Update\s*=\s*auto", "Fsr4Update=true", updated_content)
            updated_content = re.sub(r"LoadAsiPlugins\s*=\s*auto", "LoadAsiPlugins=true", updated_content)
            updated_content = re.sub(r"Path\s*=\s*auto", "Path=plugins", updated_content)
            updated_content = re.sub(r"UseHQFont\s*=\s*auto", "UseHQFont=false", updated_content)

            with open(ini_file, "w", encoding="utf-8") as f:
                f.write(updated_content)

            decky.logger.info(
                "Modified OptiScaler.ini to set FGType=nukems, Fsr4Update=true, LoadAsiPlugins=true, Path=plugins, UseHQFont=false"
            )
            return True
        except Exception as exc:
            decky.logger.error(f"Failed to modify OptiScaler.ini: {exc}")
            return False

    def _create_renamed_copies(self, source_file: Path, renames_dir: Path) -> bool:
        try:
            renames_dir.mkdir(exist_ok=True)

            rename_files = [f"{proxy}.dll" for proxy in SUPPORTED_PROXIES] + ["OptiScaler.asi"]
            if not source_file.exists():
                decky.logger.error(f"Source file {source_file} does not exist")
                return False

            for rename_file in rename_files:
                dest_file = renames_dir / rename_file
                shutil.copy2(source_file, dest_file)
                decky.logger.info(f"Created renamed copy: {dest_file}")
            return True
        except Exception as exc:
            decky.logger.error(f"Failed to create renamed copies: {exc}")
            return False

    def _copy_launcher_scripts(self, assets_dir: Path, extract_path: Path) -> bool:
        try:
            launcher_assets = {
                "fgmod.sh": "fgmod",
                "fgmod-uninstaller.sh": "fgmod-uninstaller.sh",
                "update-optiscaler-config.py": "update-optiscaler-config.py",
            }

            for asset_name, dest_name in launcher_assets.items():
                source = assets_dir / asset_name
                dest = extract_path / dest_name
                if not source.exists():
                    decky.logger.error(f"Launcher asset missing: {source}")
                    return False
                shutil.copy2(source, dest)
                dest.chmod(0o755)
                decky.logger.info(f"Copied launcher asset {source} to {dest}")

            return True
        except Exception as exc:
            decky.logger.error(f"Failed to copy launcher scripts: {exc}")
            return False

    def _cleanup_prefix(self, compatdata_dir: Path, proxy: str | None = None, remove_managed_root: bool = True) -> dict:
        managed_root = compatdata_dir / MANAGED_DIRNAME
        manifest_path = managed_root / MANIFEST_FILENAME
        manifest = self._parse_manifest_env(manifest_path)
        selected_proxy = (proxy or manifest.get("MANAGED_PROXY") or "winmm").replace(".dll", "")

        system32 = compatdata_dir / "pfx" / "drive_c" / "windows" / "system32"
        if not system32.exists() and not managed_root.exists():
            return {"status": "success", "message": f"No managed OptiScaler state found for {compatdata_dir.name}"}

        removed = []

        for filename in ["OptiScaler.ini", *SUPPORT_FILES, *LEGACY_FILES]:
            target = system32 / filename
            if target.exists():
                try:
                    if target.is_dir():
                        shutil.rmtree(target, ignore_errors=True)
                    else:
                        target.unlink()
                    removed.append(filename)
                except Exception as exc:
                    decky.logger.error(f"Failed removing {target}: {exc}")

        plugins_dir = system32 / "plugins"
        if plugins_dir.exists():
            shutil.rmtree(plugins_dir, ignore_errors=True)
            removed.append("plugins/")

        proxy_path = system32 / f"{selected_proxy}.dll"
        backup_path = system32 / f"{selected_proxy}-original.dll"
        if proxy_path.exists():
            try:
                proxy_path.unlink()
                removed.append(proxy_path.name)
            except Exception as exc:
                decky.logger.error(f"Failed removing proxy {proxy_path}: {exc}")

        if backup_path.exists():
            try:
                shutil.move(backup_path, proxy_path)
                removed.append(backup_path.name)
                decky.logger.info(f"Restored original proxy {proxy_path.name} in {system32}")
            except Exception as exc:
                decky.logger.error(f"Failed restoring backup {backup_path}: {exc}")

        if remove_managed_root and managed_root.exists():
            shutil.rmtree(managed_root, ignore_errors=True)
            removed.append(str(managed_root))

        message = f"Cleaned prefix-managed OptiScaler for app {compatdata_dir.name}"
        decky.logger.info(f"{message}; removed entries: {removed}")
        return {"status": "success", "message": message, "removed": removed}

    def _cleanup_all_managed_prefixes(self) -> list[dict]:
        cleanup_results = []
        seen = set()

        for library in self._steam_library_paths():
            compatdata_root = library / "steamapps" / "compatdata"
            if not compatdata_root.exists():
                continue

            for managed_root in compatdata_root.glob(f"*/{MANAGED_DIRNAME}"):
                compatdata_dir = managed_root.parent
                key = str(compatdata_dir)
                if key in seen:
                    continue
                seen.add(key)
                cleanup_results.append(self._cleanup_prefix(compatdata_dir))

        return cleanup_results

    async def extract_static_optiscaler(self) -> dict:
        """Extract OptiScaler from the plugin's bin directory and copy runtime assets."""
        try:
            decky.logger.info("Starting extract_static_optiscaler method")

            bin_path = Path(decky.DECKY_PLUGIN_DIR) / "bin"
            extract_path = self._bundle_path()

            if not bin_path.exists():
                decky.logger.error(f"Bin directory does not exist: {bin_path}")
                return {"status": "error", "message": f"Bin directory not found: {bin_path}"}

            optiscaler_archive = None
            for file in bin_path.glob("*.7z"):
                if ("OptiScaler" in file.name or "Optiscaler" in file.name) and "BUNDLE" not in file.name:
                    optiscaler_archive = file
                    break

            if not optiscaler_archive:
                decky.logger.error("OptiScaler archive not found in plugin bin directory")
                return {"status": "error", "message": "OptiScaler archive not found in plugin bin directory"}

            if extract_path.exists():
                shutil.rmtree(extract_path)
            extract_path.mkdir(parents=True, exist_ok=True)

            extract_cmd = ["7z", "x", "-y", "-o" + str(extract_path), str(optiscaler_archive)]
            clean_env = os.environ.copy()
            clean_env["LD_LIBRARY_PATH"] = ""

            extract_result = subprocess.run(
                extract_cmd,
                capture_output=True,
                text=True,
                check=False,
                env=clean_env,
            )

            if extract_result.returncode != 0:
                decky.logger.error(f"Extraction failed: {extract_result.stderr}")
                return {
                    "status": "error",
                    "message": f"Failed to extract OptiScaler archive: {extract_result.stderr}",
                }

            additional_files = [
                "nvngx.dll",
                "OptiPatcher_v0.30.asi",
            ]

            for file_name in additional_files:
                src_file = bin_path / file_name
                dest_file = extract_path / file_name
                if not src_file.exists():
                    return {
                        "status": "error",
                        "message": f"Required file {file_name} not found in plugin bin directory",
                    }
                shutil.copy2(src_file, dest_file)

            source_file = extract_path / "OptiScaler.dll"
            renames_dir = extract_path / "renames"
            self._create_renamed_copies(source_file, renames_dir)

            assets_dir = Path(decky.DECKY_PLUGIN_DIR) / "assets"
            if not self._copy_launcher_scripts(assets_dir, extract_path):
                return {"status": "error", "message": "Failed to install runtime launcher scripts"}

            plugins_dir = extract_path / "plugins"
            plugins_dir.mkdir(exist_ok=True)
            asi_src = bin_path / "OptiPatcher_v0.30.asi"
            if asi_src.exists():
                shutil.copy2(asi_src, plugins_dir / "OptiPatcher.asi")

            try:
                skip_overwrite = os.environ.get("DECKY_SKIP_UPSCALER_OVERWRITE", "false").lower() in ("1", "true", "yes")
                if UPSCALER_OVERWRITE_ENABLED and not skip_overwrite:
                    upscaler_src = bin_path / "amd_fidelityfx_upscaler_dx12.dll"
                    upscaler_dst = extract_path / "amd_fidelityfx_upscaler_dx12.dll"
                    if upscaler_src.exists():
                        shutil.copy2(upscaler_src, upscaler_dst)
                        decky.logger.info("Overwrote amd_fidelityfx_upscaler_dx12.dll with static remote binary")
                else:
                    decky.logger.info("Skipping upscaler DLL overwrite due to DECKY_SKIP_UPSCALER_OVERWRITE")
            except Exception as exc:
                decky.logger.error(f"Failed upscaler overwrite step: {exc}")

            version_match = optiscaler_archive.name.replace(".7z", "")
            if "OptiScaler_" in version_match:
                version = "v" + version_match.split("OptiScaler_")[1]
            elif "Optiscaler_" in version_match:
                version = "v" + version_match.split("Optiscaler_")[1]
            else:
                version = version_match

            with open(extract_path / "version.txt", "w", encoding="utf-8") as f:
                f.write(version)

            ini_file = extract_path / "OptiScaler.ini"
            self._modify_optiscaler_ini(ini_file)

            return {
                "status": "success",
                "message": f"Installed prefix-managed OptiScaler runtime {version} to {extract_path}",
                "version": version,
            }

        except Exception as exc:
            decky.logger.error(f"Extract failed with exception: {str(exc)}")
            import traceback

            decky.logger.error(f"Traceback: {traceback.format_exc()}")
            return {"status": "error", "message": f"Extract failed: {str(exc)}"}

    async def run_uninstall_fgmod(self) -> dict:
        try:
            cleanup_results = self._cleanup_all_managed_prefixes()
            bundle_path = self._bundle_path()

            if bundle_path.exists():
                shutil.rmtree(bundle_path)
                decky.logger.info(f"Removed directory: {bundle_path}")

            cleaned_prefixes = len([result for result in cleanup_results if result.get("status") == "success"])
            return {
                "status": "success",
                "output": f"Removed OptiScaler runtime and cleaned {cleaned_prefixes} managed compatdata prefixes.",
            }
        except Exception as exc:
            decky.logger.error(f"Uninstall error: {str(exc)}")
            return {
                "status": "error",
                "message": f"Uninstall failed: {str(exc)}",
                "output": str(exc),
            }

    async def run_install_fgmod(self) -> dict:
        try:
            decky.logger.info("Starting OptiScaler installation from static bundle")
            extract_result = await self.extract_static_optiscaler()
            if extract_result["status"] != "success":
                return {
                    "status": "error",
                    "message": f"OptiScaler extraction failed: {extract_result.get('message', 'Unknown error')}",
                }

            return {
                "status": "success",
                "output": "Installed the prefix-managed OptiScaler runtime. Use the game selector or launch command to stage it inside a Proton prefix at launch time.",
            }
        except Exception as exc:
            decky.logger.error(f"Unexpected error during installation: {str(exc)}")
            return {"status": "error", "message": f"Installation failed: {str(exc)}"}

    async def check_fgmod_path(self) -> dict:
        path = self._bundle_path()
        if not path.exists():
            return {"exists": False}

        for file_name in REQUIRED_BUNDLE_FILES:
            if not path.joinpath(file_name).exists():
                return {"exists": False}

        plugins_dir = path / "plugins"
        if not plugins_dir.exists() or not (plugins_dir / "OptiPatcher.asi").exists():
            return {"exists": False}

        return {"exists": True}

    async def cleanup_managed_game(self, appid: str) -> dict:
        compatdata_dirs = self._compatdata_dirs_for_appid(str(appid))
        if not compatdata_dirs:
            return {"status": "success", "message": f"No compatdata prefix found for app {appid}; launch options can still be cleared."}

        cleanup_messages = []
        for compatdata_dir in compatdata_dirs:
            result = self._cleanup_prefix(compatdata_dir)
            cleanup_messages.append(result.get("message", f"Cleaned {compatdata_dir}"))

        return {"status": "success", "message": "\n".join(cleanup_messages)}

    async def get_game_config(self, appid: str) -> dict:
        try:
            paths = self._ensure_managed_ini(str(appid))
            manifest = self._parse_manifest_env(paths["manifest_path"])
            installed_game = self._find_installed_game(str(appid))
            game_name = installed_game[0]["name"] if installed_game else str(appid)

            source_ini = paths["live_ini"] if paths["live_ini"].exists() else paths["managed_ini"]
            with open(source_ini, "r", encoding="utf-8", errors="replace") as ini_file:
                raw_ini = ini_file.read()

            preferred_proxy = manifest.get("PREFERRED_PROXY") or manifest.get("MANAGED_PROXY") or "winmm"
            proxy = self._normalize_proxy(preferred_proxy)
            schema = self._parse_ini_schema(self._bundle_ini_path())
            settings = self._extract_all_settings(source_ini, schema)

            return {
                "status": "success",
                "appid": str(appid),
                "name": game_name,
                "proxy": proxy,
                "settings": settings,
                "schema": schema,
                "raw_ini": raw_ini,
                "managed_exists": paths["managed_ini"].exists(),
                "live_available": paths["live_ini"].exists(),
                "paths": {
                    "compatdata": str(paths["compatdata_dir"]),
                    "managed_root": str(paths["managed_root"]),
                    "managed_ini": str(paths["managed_ini"]),
                    "system32": str(paths["system32"]),
                    "live_ini": str(paths["live_ini"]),
                },
            }
        except Exception as exc:
            decky.logger.error(f"get_game_config failed for {appid}: {exc}")
            return {"status": "error", "message": str(exc)}

    async def save_game_config(
        self,
        appid: str,
        settings: dict | None = None,
        proxy: str | None = None,
        apply_live: bool = False,
        raw_ini: str | None = None,
    ) -> dict:
        try:
            paths = self._ensure_managed_ini(str(appid))
            manifest_updates = {}
            if proxy:
                manifest_updates["PREFERRED_PROXY"] = self._normalize_proxy(proxy)
            if manifest_updates:
                self._write_manifest_env(paths["manifest_path"], manifest_updates)

            managed_ini = paths["managed_ini"]
            resolved_updates = []
            settings = settings or {}
            schema_lookup = self._schema_lookup(self._parse_ini_schema(self._bundle_ini_path()))

            if raw_ini is not None:
                with open(managed_ini, "w", encoding="utf-8") as ini_file:
                    ini_file.write(raw_ini)
            elif settings:
                for setting_id, value in settings.items():
                    definition = schema_lookup.get(setting_id)
                    if not definition:
                        continue
                    resolved_updates.append((definition["section"], definition["key"], str(value)))
                if resolved_updates:
                    self._replace_ini_values(managed_ini, resolved_updates)

            self._disable_hq_font_auto(managed_ini)

            live_applied = False
            if apply_live and paths["live_ini"].exists():
                if raw_ini is not None:
                    with open(paths["live_ini"], "w", encoding="utf-8") as ini_file:
                        ini_file.write(raw_ini)
                elif resolved_updates:
                    self._replace_ini_values(paths["live_ini"], resolved_updates)
                self._disable_hq_font_auto(paths["live_ini"])
                live_applied = True

            message = "Saved OptiScaler config"
            if apply_live:
                message = (
                    "Saved OptiScaler config and applied it to the running game's live prefix copy"
                    if live_applied
                    else "Saved OptiScaler config, but no live prefix copy was available to update"
                )

            updated_config = await self.get_game_config(appid)
            if updated_config.get("status") != "success":
                return {
                    "status": "success",
                    "message": message,
                    "live_applied": live_applied,
                    "proxy": self._parse_manifest_env(paths["manifest_path"]).get("PREFERRED_PROXY", proxy or "winmm"),
                }

            updated_config["message"] = message
            updated_config["live_applied"] = live_applied
            return updated_config
        except Exception as exc:
            decky.logger.error(f"save_game_config failed for {appid}: {exc}")
            return {"status": "error", "message": str(exc)}

    async def list_installed_games(self) -> dict:
        try:
            games = self._find_installed_game()
            sanitized_games = [{"appid": game["appid"], "name": game["name"]} for game in games]
            return {"status": "success", "games": sanitized_games}
        except Exception as exc:
            decky.logger.error(str(exc))
            return {"status": "error", "message": str(exc)}

    async def get_path_defaults(self) -> dict:
        home_path = self._home_path()
        steam_common = home_path / ".local" / "share" / "Steam" / "steamapps" / "common"
        return {
            "home": str(home_path),
            "steam_common": str(steam_common),
        }

    async def log_error(self, error: str) -> None:
        decky.logger.error(f"FRONTEND: {error}")

    async def manual_patch_directory(self, directory: str) -> dict:
        return {
            "status": "error",
            "message": "Direct game-directory patching has been removed. Use the prefix-managed launch command instead.",
        }

    async def manual_unpatch_directory(self, directory: str) -> dict:
        return {
            "status": "error",
            "message": "Direct game-directory patching has been removed. Use the prefix-managed launch command or per-game cleanup instead.",
        }

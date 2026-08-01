"""OptiScaler configuration migration and default handling."""

import re
from pathlib import Path
from typing import Callable


Logger = Callable[[str], None]


def _split_override_key(raw_key: str) -> tuple[str | None, str]:
    key = str(raw_key).strip()
    if "." in key:
        section, section_key = key.split(".", 1)
        section = section.strip()
        section_key = section_key.strip()
        if section and section_key:
            return section, section_key
    return None, key


def apply_overrides(ini_file: Path, overrides: dict, logger: Logger | None = None) -> bool:
    """Upsert INI keys without disturbing unrelated game configuration."""
    if not overrides:
        return True
    try:
        content = ini_file.read_text(encoding="utf-8", errors="replace")
        newline = "\r\n" if "\r\n" in content else "\n"
        lines = content.splitlines(keepends=True)
        section_pattern = re.compile(r"^\s*\[(?P<section>[^\]]+)\]\s*$")

        def ensure_trailing_newline() -> None:
            if lines and not lines[-1].endswith(("\n", "\r")):
                lines[-1] += newline

        def upsert(section: str | None, key: str, value: str) -> None:
            replacement = f"{key}={value}"
            key_pattern = re.compile(rf"^(\s*{re.escape(key)}\s*)=.*$")

            if section is None:
                for index, line in enumerate(lines):
                    if key_pattern.match(line):
                        ending = "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else newline)
                        lines[index] = f"{replacement}{ending}"
                        return
                ensure_trailing_newline()
                lines.append(f"{replacement}{newline}")
                return

            in_section = False
            insert_at = None
            for index, line in enumerate(lines):
                match = section_pattern.match(line.strip())
                if match:
                    if in_section:
                        insert_at = index
                        break
                    if match.group("section") == section:
                        in_section = True
                        continue
                if in_section and key_pattern.match(line):
                    ending = "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else newline)
                    lines[index] = f"{replacement}{ending}"
                    return

            if in_section:
                if insert_at is None:
                    ensure_trailing_newline()
                    insert_at = len(lines)
                lines.insert(insert_at, f"{replacement}{newline}")
                return

            ensure_trailing_newline()
            if lines and lines[-1].strip():
                lines.append(newline)
            lines.extend((f"[{section}]{newline}", f"{replacement}{newline}"))

        for raw_key, raw_value in overrides.items():
            section, key = _split_override_key(str(raw_key))
            if key:
                upsert(section, key, str(raw_value).strip())
        ini_file.write_text("".join(lines), encoding="utf-8")
        return True
    except Exception as exc:
        if logger:
            logger(f"Failed to apply OptiScaler.ini overrides to {ini_file}: {exc}")
        return False


def migrate(ini_file: Path, logger: Logger | None = None) -> bool:
    """Migrate the pre-0.9 ``FGType`` setting to split input/output keys."""
    try:
        if not ini_file.exists():
            return False
        content = ini_file.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^FGType\s*=\s*(\S+)", content, re.MULTILINE)
        if not match:
            return True

        value = match.group(1)
        if re.search(r"^FGInput\s*=", content, re.MULTILINE):
            updated = re.sub(r"^FGType\s*=\s*\S+\n?", "", content, flags=re.MULTILINE)
            message = f"Removed stale FGType from {ini_file}"
        else:
            updated = re.sub(
                r"^FGType\s*=\s*\S+",
                f"FGInput={value}\nFGOutput={value}",
                content,
                flags=re.MULTILINE,
            )
            message = f"Migrated FGType={value} in {ini_file}"
        if updated != content:
            ini_file.write_text(updated, encoding="utf-8")
            if logger:
                logger(message)
        return True
    except Exception as exc:
        if logger:
            logger(f"Failed to migrate OptiScaler.ini: {exc}")
        return False


def disable_hq_font_auto(ini_file: Path, logger: Logger | None = None) -> bool:
    """Avoid the HQ font auto mode, which is unreliable under Proton."""
    try:
        if not ini_file.exists():
            return False
        content = ini_file.read_text(encoding="utf-8", errors="replace")
        updated = re.sub(r"UseHQFont\s*=\s*auto", "UseHQFont=false", content)
        if updated != content:
            ini_file.write_text(updated, encoding="utf-8")
        return True
    except Exception as exc:
        if logger:
            logger(f"Failed to update HQ font setting in {ini_file}: {exc}")
        return False


def configure(
    ini_file: Path,
    framegen_backend: str,
    variant_overrides: dict | None = None,
    logger: Logger | None = None,
) -> bool:
    """Apply safe defaults and the selected frame-generation backend."""
    if not ini_file.exists():
        return False
    backend = framegen_backend if framegen_backend in {"auto", "nukems"} else "auto"
    overrides = {
        "FGInput": backend,
        "FGOutput": backend,
        "Fsr4Update": "true",
        "LoadAsiPlugins": "true",
    }
    if variant_overrides:
        overrides.update(variant_overrides)
    migrated = migrate(ini_file, logger)
    hq_updated = disable_hq_font_auto(ini_file, logger)
    configured = apply_overrides(ini_file, overrides, logger)
    return migrated and hq_updated and configured


def detect_backend(ini_file: Path) -> str:
    """Return the configured backend when both FG keys agree."""
    try:
        content = ini_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "auto"
    values = [
        match.group(1).strip().lower()
        for match in re.finditer(r"^FG(?:Input|Output)\s*=\s*(\S+)", content, re.MULTILINE)
    ]
    if values and all(value == "nukems" for value in values):
        return "nukems"
    return "auto"

"""Patch ownership, safe cleanup, and Steam-game operations."""

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import config
from .assets import (
    BACKUP_DIRECTORY_NAME,
    FRAMEGEN_BACKENDS,
    FSR4_UPSCALER_FILENAME,
    INJECTOR_FILENAMES,
    MARKER_FILENAME,
    MANIFEST_SCHEMA_VERSION,
    RESTORABLE_BACKUP_FILES,
    SUPPORT_FILES,
    VALID_DLL_NAMES,
    VARIANT_EXTRA_FILENAMES,
)
from .bundle import BundleManager
from .files import file_sha256, files_match, read_json, write_json
from .steam import SteamLibrary


Logger = Callable[[str], None]


class PatchManager:
    def __init__(self, home: Path, bundle: BundleManager, steam: SteamLibrary, logger: Logger):
        self.home = home
        self.bundle = bundle
        self.steam = steam
        self.logger = logger

    def _log(self, message: str) -> None:
        self.logger(f"[Framegen] {message}")

    @staticmethod
    def _relative_path(root: Path, path: Path) -> str:
        return path.resolve().relative_to(root.resolve()).as_posix()

    def _safe_path(self, root: Path, value: str | Path) -> Path:
        candidate = Path(value)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (root / candidate).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError(f"Path escapes patch directory: {value}") from exc
        return resolved

    def _read_marker(self, marker_path: Path) -> dict:
        return read_json(marker_path)

    def _find_marker(self, install_root: Path, appid: str | None = None) -> Path | None:
        if not install_root.exists():
            return None
        try:
            markers = sorted(path for path in install_root.rglob(MARKER_FILENAME) if path.is_file())
        except OSError:
            return None
        for marker in markers:
            metadata = self._read_marker(marker)
            if appid is None or str(metadata.get("appid")) == str(appid):
                return marker
        return None

    def _marker_target(self, marker_path: Path, metadata: dict) -> Path:
        target_value = metadata.get("target_relative") or metadata.get("target_dir") or str(marker_path.parent)
        target = self._safe_path(marker_path.parent, target_value)
        if not target.is_dir():
            raise FileNotFoundError(f"Patch target directory does not exist: {target}")
        return target

    def _bundle_source_for_proxy(self, variant: str, dll_name: str) -> Path:
        candidates = [
            self.bundle.variant_proxy_path(variant, dll_name),
            self.bundle.variant_injector_path(variant),
            self.bundle.fgmod_path / "renames" / dll_name,
            self.bundle.fgmod_path / "OptiScaler.dll",
        ]
        for candidate in candidates:
            if candidate and candidate.exists():
                return candidate
        raise FileNotFoundError(f"No injector source found for {dll_name}")

    def _copy_plan(self, target_dir: Path, variant: str) -> list[tuple[str, Path]]:
        plan: list[tuple[str, Path]] = []
        # The proxy is the only file selected by the user; all other files are bundle-owned.
        plan.append(("__proxy__", self._bundle_source_for_proxy(variant, "dxgi.dll")))
        for filename in SUPPORT_FILES:
            source = self.bundle.fgmod_path / filename
            if source.is_file():
                plan.append((filename, source))
        upscaler = self.bundle.variant_path(variant)
        if upscaler.is_file():
            plan.append((FSR4_UPSCALER_FILENAME, upscaler))
        for extra in self.bundle.variant_extra_files(variant):
            source = self.bundle.variant_extra_path(variant, extra["name"])
            if source.is_file():
                plan.append((extra["name"], source))

        for source_root, relative_root in (
            (self.bundle.fgmod_path / "plugins", Path("plugins")),
            (self.bundle.fgmod_path / "D3D12_Optiscaler", Path("D3D12_Optiscaler")),
        ):
            if not source_root.is_dir():
                continue
            for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
                plan.append(((relative_root / source.relative_to(source_root)).as_posix(), source))
        return plan

    def _backup_destination(self, target_dir: Path, relative: str, source: Path, force: bool = False) -> str | None:
        destination = self._safe_path(target_dir, relative)
        if not destination.exists():
            return None
        if destination.is_dir():
            raise IsADirectoryError(f"Patch destination is a directory: {destination}")
        if not force and files_match(destination, source):
            return None

        if relative in RESTORABLE_BACKUP_FILES:
            legacy_backup = destination.with_name(destination.name + ".b")
            if not legacy_backup.exists():
                shutil.copy2(destination, legacy_backup)
            elif not files_match(legacy_backup, destination):
                raise RuntimeError(f"Refusing to overwrite an existing backup: {legacy_backup}")
            return self._relative_path(target_dir, legacy_backup)

        backup = target_dir / BACKUP_DIRECTORY_NAME / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        if backup.exists():
            if not files_match(backup, destination):
                raise RuntimeError(f"Refusing to overwrite an existing backup: {backup}")
        else:
            shutil.copy2(destination, backup)
        return self._relative_path(target_dir, backup)

    def _cleanup_empty_directories(self, target_dir: Path, managed_files: list[str]) -> None:
        directories = sorted(
            {self._safe_path(target_dir, path).parent for path in managed_files},
            key=lambda path: len(path.parts),
            reverse=True,
        )
        for directory in directories:
            if directory == target_dir:
                continue
            try:
                directory.rmdir()
            except OSError:
                pass
        backup_dir = target_dir / BACKUP_DIRECTORY_NAME
        try:
            backup_dir.rmdir()
        except OSError:
            pass

    def _rollback(
        self,
        target_dir: Path,
        managed: list[dict],
        backups: list[dict],
    ) -> None:
        for entry in reversed(managed):
            try:
                path = self._safe_path(target_dir, entry["path"])
                backup = next((item["backup"] for item in backups if item["path"] == entry["path"]), None)
                if backup:
                    backup_path = self._safe_path(target_dir, backup)
                    if backup_path.exists():
                        if path.exists():
                            path.unlink()
                        shutil.move(backup_path, path)
                elif path.exists() and entry.get("sha256") == file_sha256(path):
                    path.unlink()
            except (OSError, ValueError):
                continue
        self._cleanup_empty_directories(target_dir, [entry["path"] for entry in managed])

    def _patch_directory(
        self,
        target_dir: Path,
        dll_name: str,
        variant: str,
        framegen_backend: str,
        *,
        appid: str,
        game_name: str,
        original_launch_options: str,
        previous_variant: str | None = None,
    ) -> dict:
        if dll_name not in VALID_DLL_NAMES:
            return {"status": "error", "message": f"Invalid proxy DLL name: {dll_name}"}
        if not self.bundle.fgmod_path.exists() or not (self.bundle.fgmod_path / "OptiScaler.dll").exists():
            return {"status": "error", "message": "OptiScaler bundle not installed. Run Install first."}

        variant = self.bundle.selected_variant(variant)
        framegen_backend = self.bundle.selected_backend(framegen_backend)
        previous_marker = target_dir / MARKER_FILENAME
        if previous_marker.exists():
            return {"status": "error", "message": f"Patch marker already exists in {target_dir}; clean it up before patching."}
        variant_overrides = self.bundle.variant_config_overrides(variant)
        if previous_variant == "rdna2-valve-411-pre10" and variant != previous_variant:
            variant_overrides.setdefault("FSR.Fsr4ForceModel", "auto")
            variant_overrides.setdefault("Plugins.LoadCustomAmdxc64OnRdna2", "false")

        managed: list[dict] = []
        backups: list[dict] = []
        try:
            plan = self._copy_plan(target_dir, variant)
            proxy_source = self._bundle_source_for_proxy(variant, dll_name)
            plan[0] = (dll_name, proxy_source)
            config_path = target_dir / "OptiScaler.ini"
            if config_path.exists():
                plan.append(("OptiScaler.ini", config_path))
            elif (self.bundle.fgmod_path / "OptiScaler.ini").exists():
                plan.append(("OptiScaler.ini", self.bundle.fgmod_path / "OptiScaler.ini"))

            for relative, source in plan:
                destination = self._safe_path(target_dir, relative)
                if not source.is_file():
                    continue
                backup = self._backup_destination(
                    target_dir,
                    relative,
                    source,
                    # Preserve every pre-existing destination. Identical bytes do
                    # not prove that a file belongs to this plugin.
                    force=destination.exists(),
                )
                if backup:
                    backups.append({
                        "path": relative,
                        "backup": backup,
                        "sha256": file_sha256(self._safe_path(target_dir, backup)),
                    })
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.resolve() != source.resolve():
                    shutil.copy2(source, destination)
                managed.append({
                    "path": relative,
                    "sha256": file_sha256(destination),
                    "source_sha256": file_sha256(source),
                })

            if config_path.exists() and not config.configure(
                config_path,
                framegen_backend,
                variant_overrides=variant_overrides,
                logger=self.logger,
            ):
                raise RuntimeError("Could not update OptiScaler.ini")
            config_entry = next((entry for entry in managed if entry["path"] == "OptiScaler.ini"), None)
            if config_entry:
                config_entry["sha256"] = file_sha256(config_path)

            payload = {
                "schema_version": MANIFEST_SCHEMA_VERSION,
                "appid": str(appid),
                "game_name": game_name,
                "dll_name": dll_name,
                "target_dir": str(target_dir),
                "target_relative": ".",
                "original_launch_options": original_launch_options,
                "backed_up_files": [item["path"] for item in backups],
                "backups": backups,
                "managed_files": managed,
                "managed_directories": sorted({str(Path(item["path"]).parent) for item in managed if Path(item["path"]).parent != Path(".")}),
                "optiscaler_version": self.bundle.fgmod_version(),
                "fsr4_variant": variant,
                "fsr4_variant_label": self.bundle.variant_info(variant)["label"],
                "fsr4_upscaler_sha256": file_sha256(target_dir / FSR4_UPSCALER_FILENAME) if (target_dir / FSR4_UPSCALER_FILENAME).exists() else None,
                "framegen_backend": framegen_backend,
                "framegen_backend_label": FRAMEGEN_BACKENDS[framegen_backend],
                "patched_at": datetime.now(timezone.utc).isoformat(),
            }
            # The marker is written last, so an interrupted copy is never advertised as a complete patch.
            write_json(previous_marker, payload)
            return {
                "status": "success",
                "message": f"OptiScaler files copied to {target_dir} using {self.bundle.variant_info(variant)['label']}",
                "fsr4_variant": variant,
                "fsr4_variant_label": self.bundle.variant_info(variant)["label"],
                "fsr4_upscaler_sha256": payload["fsr4_upscaler_sha256"],
                "optiscaler_version": payload["optiscaler_version"],
                "framegen_backend": framegen_backend,
            }
        except (OSError, RuntimeError, ValueError) as exc:
            self._rollback(target_dir, managed, backups)
            self._log(f"Patch failed for {target_dir}: {exc}")
            return {"status": "error", "message": f"Patch failed: {exc}"}

    def _managed_entries(self, target_dir: Path, metadata: dict) -> tuple[list[tuple[dict, Path]], list[str]]:
        entries: list[tuple[dict, Path]] = []
        errors: list[str] = []
        for entry in metadata.get("managed_files", []):
            if not isinstance(entry, dict) or not entry.get("path"):
                errors.append("Patch marker contains an invalid managed file entry.")
                continue
            try:
                path = self._safe_path(target_dir, entry["path"])
            except ValueError as exc:
                errors.append(str(exc))
                continue
            expected = str(entry.get("sha256") or "")
            if not expected:
                errors.append(f"Patch marker has no hash for {entry['path']}.")
            elif path.exists() and (not path.is_file() or file_sha256(path).lower() != expected.lower()):
                errors.append(f"Refusing to remove modified managed file: {path}")
            entries.append((entry, path))
        return entries, errors

    def _restore_backups(self, target_dir: Path, metadata: dict) -> list[str]:
        restored: list[str] = []
        for item in metadata.get("backups", []):
            if not isinstance(item, dict) or not item.get("path") or not item.get("backup"):
                raise ValueError("Patch marker contains an invalid backup entry.")
            path = self._safe_path(target_dir, item["path"])
            backup = self._safe_path(target_dir, item["backup"])
            if not backup.exists():
                continue
            if not backup.is_file():
                raise ValueError(f"Patch backup is not a file: {backup}")
            expected = str(item.get("sha256") or "")
            if expected and file_sha256(backup).lower() != expected.lower():
                raise RuntimeError(f"Refusing to restore a modified backup: {backup}")
            if path.exists():
                raise RuntimeError(f"Refusing to overwrite a file while restoring backup: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(backup, path)
            restored.append(str(item["path"]))

        # Older releases used ``name.b`` backups and listed only their base names.
        for raw_name in metadata.get("backed_up_files", []):
            name = Path(str(raw_name)).name
            if name not in RESTORABLE_BACKUP_FILES:
                continue
            original = self._safe_path(target_dir, name)
            backup = self._safe_path(target_dir, name + ".b")
            if backup.exists() and not original.exists():
                shutil.move(backup, original)
                restored.append(name)
        return restored

    def _validate_backups(self, target_dir: Path, metadata: dict) -> None:
        for item in metadata.get("backups", []):
            if not isinstance(item, dict) or not item.get("path") or not item.get("backup"):
                raise ValueError("Patch marker contains an invalid backup entry.")
            self._safe_path(target_dir, item["path"])
            backup = self._safe_path(target_dir, item["backup"])
            if not backup.exists():
                continue
            if not backup.is_file():
                raise ValueError(f"Patch backup is not a file: {backup}")
            expected = str(item.get("sha256") or "")
            if expected and file_sha256(backup).lower() != expected.lower():
                raise RuntimeError(f"Refusing to restore a modified backup: {backup}")

    def _legacy_owned_paths(self, target_dir: Path, metadata: dict) -> list[Path]:
        paths: list[Path] = []
        for entry in metadata.get("managed_files", []):
            if isinstance(entry, dict) and entry.get("path"):
                try:
                    paths.append(self._safe_path(target_dir, entry["path"]))
                except ValueError:
                    continue

        variant = self.bundle.normalize_variant(metadata.get("fsr4_variant"))
        proxy_sources = [
            self.bundle.fgmod_path / "OptiScaler.dll",
            self.bundle.fgmod_path / "renames",
            self.bundle.variant_dir(variant) / "renames",
        ]
        for filename in INJECTOR_FILENAMES:
            target = target_dir / filename
            if not target.is_file():
                continue
            matches_bundle = False
            for source in proxy_sources:
                candidate = source if source.is_file() and source.name == filename else source / filename
                if candidate.is_file() and files_match(target, candidate):
                    matches_bundle = True
                    break
            if matches_bundle:
                paths.append(target)
        for filename in SUPPORT_FILES + VARIANT_EXTRA_FILENAMES + [FSR4_UPSCALER_FILENAME]:
            target = target_dir / filename
            if target.is_file() and self.bundle.is_managed_support_file(target):
                paths.append(target)
        for relative in (Path("plugins/OptiPatcher.asi"),):
            target = target_dir / relative
            source = self.bundle.fgmod_path / relative
            if target.is_file() and source.is_file() and files_match(target, source):
                paths.append(target)
        d3d12_source = self.bundle.fgmod_path / "D3D12_Optiscaler"
        d3d12_target = target_dir / "D3D12_Optiscaler"
        if d3d12_source.is_dir() and d3d12_target.is_dir():
            for source in d3d12_source.rglob("*"):
                if source.is_file():
                    candidate = d3d12_target / source.relative_to(d3d12_source)
                    if candidate.is_file() and files_match(candidate, source):
                        paths.append(candidate)
        unique: list[Path] = []
        seen: set[str] = set()
        for path in paths:
            if str(path) not in seen:
                unique.append(path)
                seen.add(str(path))
        return unique

    def _unpatch_target(self, target_dir: Path, marker_path: Path | None) -> dict:
        metadata = self._read_marker(marker_path) if marker_path else {
            "backed_up_files": [
                name for name in RESTORABLE_BACKUP_FILES
                if (target_dir / f"{name}.b").is_file()
            ],
        }
        try:
            if marker_path and marker_path.exists() and not metadata:
                return {"status": "error", "message": f"Patch marker is unreadable: {marker_path}"}
            schema_version = int(metadata.get("schema_version") or 1) if metadata else 1
            if schema_version >= MANIFEST_SCHEMA_VERSION:
                entries, errors = self._managed_entries(target_dir, metadata)
                if errors:
                    return {"status": "error", "message": " ".join(errors)}
                self._validate_backups(target_dir, metadata)
                managed_paths = [path for _, path in entries]
                for _, path in entries:
                    if path.exists():
                        path.unlink()
                restored = self._restore_backups(target_dir, metadata)
                self._cleanup_empty_directories(target_dir, [str(path.relative_to(target_dir)) for path in managed_paths])
            else:
                owned = self._legacy_owned_paths(target_dir, metadata)
                entries, errors = self._managed_entries(target_dir, metadata)
                if errors:
                    return {"status": "error", "message": " ".join(errors)}
                owned.extend(path for _, path in entries if path not in owned)
                for path in owned:
                    if path.is_file():
                        path.unlink()
                restored = self._restore_backups(target_dir, metadata)
                self._cleanup_empty_directories(target_dir, [str(path.relative_to(target_dir)) for path in owned])
            if marker_path and marker_path.exists():
                marker_path.unlink()
            return {
                "status": "success",
                "message": f"OptiScaler files removed from {target_dir}",
                "restored_files": restored,
            }
        except (OSError, RuntimeError, ValueError) as exc:
            self._log(f"Unpatch failed for {target_dir}: {exc}")
            return {"status": "error", "message": f"Unpatch failed: {exc}"}

    def resolve_target_directory(self, directory: str) -> Path:
        target = Path(directory).expanduser()
        if not target.exists():
            raise FileNotFoundError(f"Target directory does not exist: {directory}")
        if not target.is_dir():
            raise NotADirectoryError(f"Target path is not a directory: {directory}")
        if not os.access(target, os.W_OK | os.X_OK):
            raise PermissionError(f"Insufficient permissions for {directory}")
        return target.resolve()

    def manual_patch_directory(
        self,
        directory: str,
        dll_name: str,
        fsr4_variant: str,
        framegen_backend: str | None = None,
    ) -> dict:
        try:
            target = self.resolve_target_directory(directory)
        except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
            return {"status": "error", "message": str(exc)}
        marker = target / MARKER_FILENAME
        previous_metadata = self._read_marker(marker) if marker.exists() else {}
        previous_variant = previous_metadata.get("fsr4_variant")
        if marker.exists():
            if str(previous_metadata.get("appid")) not in ("", "manual", "None"):
                return {"status": "error", "message": "This directory is managed by an AppID patch; unpatch it there first."}
            cleanup = self._unpatch_target(target, marker)
            if cleanup["status"] != "success":
                return cleanup
        return self._patch_directory(
            target,
            dll_name,
            self.bundle.selected_variant(fsr4_variant),
            self.bundle.selected_backend(framegen_backend),
            appid="manual",
            game_name="Manual patch",
            original_launch_options="",
            previous_variant=previous_variant,
        )

    def manual_unpatch_directory(self, directory: str) -> dict:
        try:
            target = self.resolve_target_directory(directory)
        except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
            return {"status": "error", "message": str(exc)}
        marker = target / MARKER_FILENAME
        return self._unpatch_target(target, marker if marker.exists() else None)

    def list_installed_games(self) -> dict:
        try:
            return {
                "status": "success",
                "games": [
                    {
                        "appid": str(game["appid"]),
                        "name": game["name"],
                        "install_found": Path(game["install_path"]).exists(),
                    }
                    for game in self.steam.find_installed_games()
                ],
            }
        except Exception as exc:
            self._log(str(exc))
            return {"status": "error", "message": str(exc)}

    def get_game_status(self, appid: str) -> dict:
        try:
            game_info = self.steam.game_record(str(appid))
            if not game_info:
                return {
                    "status": "success", "appid": str(appid), "install_found": False, "patched": False,
                    "dll_name": None, "target_dir": None, "fsr4_variant": None, "fsr4_variant_label": None,
                    "framegen_backend": None, "message": "Game not found in Steam library.",
                }
            install_root = Path(game_info["install_path"])
            base = {
                "status": "success", "appid": str(appid), "name": game_info["name"],
                "install_found": install_root.exists(), "patched": False, "dll_name": None,
                "target_dir": None, "fsr4_variant": None, "fsr4_variant_label": None,
                "framegen_backend": None,
            }
            if not install_root.exists():
                return {**base, "message": "Game install directory not found."}
            marker = self._find_marker(install_root, str(appid))
            if not marker:
                return {**base, "message": "Not patched."}
            metadata = self._read_marker(marker)
            target_dir = self._marker_target(marker, metadata)
            dll_name = str(metadata.get("dll_name") or "dxgi.dll")
            upscaler = target_dir / FSR4_UPSCALER_FILENAME
            upscaler_sha256 = file_sha256(upscaler) if upscaler.is_file() else None
            variant = self.bundle.detect_variant(target_dir, upscaler_sha256) or self.bundle.normalize_variant(metadata.get("fsr4_variant"))
            backend = self.bundle.normalize_backend(metadata.get("framegen_backend") or self.bundle.selected_backend())
            dll_present = (target_dir / dll_name).is_file()
            return {
                **base,
                "patched": dll_present,
                "dll_name": dll_name,
                "target_dir": str(target_dir),
                "patched_at": metadata.get("patched_at"),
                "optiscaler_version": metadata.get("optiscaler_version"),
                "fsr4_variant": variant,
                "fsr4_variant_label": self.bundle.variant_info(variant)["label"],
                "fsr4_upscaler_sha256": upscaler_sha256,
                "framegen_backend": backend,
                "framegen_backend_label": FRAMEGEN_BACKENDS[backend],
                "message": f"Patched using {dll_name} with {self.bundle.variant_info(variant)['label']}." if dll_present else f"Marker found but {dll_name} is missing. Reinstall recommended.",
            }
        except Exception as exc:
            self._log(f"get_game_status failed for {appid}: {exc}")
            return {"status": "error", "message": str(exc)}

    @staticmethod
    def build_managed_launch_options(dll_name: str) -> str:
        if dll_name == "OptiScaler.asi":
            return "SteamDeck=0 %command%"
        base = dll_name.replace(".dll", "")
        return f"WINEDLLOVERRIDES={base}=n,b SteamDeck=0 %command%"

    @staticmethod
    def is_managed_launch_options(options: str) -> bool:
        normalized = " ".join((options or "").replace('"', "").split())
        if not normalized:
            return False
        return any(
            dll_name != "OptiScaler.asi" and f"WINEDLLOVERRIDES={dll_name.replace('.dll', '')}=n,b" in normalized
            for dll_name in VALID_DLL_NAMES
        ) or "fgmod/fgmod" in normalized

    def patch_game(
        self,
        appid: str,
        dll_name: str,
        current_launch_options: str,
        fsr4_variant: str,
        framegen_backend: str | None = None,
    ) -> dict:
        try:
            if dll_name not in VALID_DLL_NAMES:
                return {"status": "error", "message": f"Invalid proxy DLL name: {dll_name}"}
            game_info = self.steam.game_record(str(appid))
            if not game_info:
                return {"status": "error", "message": "Game not found in Steam library."}
            install_root = Path(game_info["install_path"])
            if not install_root.exists():
                return {"status": "error", "message": "Game install directory does not exist."}
            if self.steam.is_game_running(game_info):
                return {"status": "error", "message": "Close the game before patching."}
            if not self.bundle.fgmod_path.exists():
                return {"status": "error", "message": "OptiScaler bundle not installed. Run Install first."}

            existing_marker = self._find_marker(install_root)
            existing_metadata = self._read_marker(existing_marker) if existing_marker else {}
            if existing_marker and str(existing_metadata.get("appid")) not in (str(appid), "manual", "None"):
                return {"status": "error", "message": "Another Framegen patch marker was found in this game install."}
            original_options = current_launch_options or ""
            stored_options = str(existing_metadata.get("original_launch_options") or "")
            if stored_options and not self.is_managed_launch_options(stored_options):
                original_options = stored_options
            if self.is_managed_launch_options(original_options):
                original_options = ""

            if existing_marker:
                old_target = self._marker_target(existing_marker, existing_metadata)
                cleanup = self._unpatch_target(old_target, existing_marker)
                if cleanup["status"] != "success":
                    return cleanup
            target_dir, _ = self.steam.guess_patch_target(game_info)
            result = self._patch_directory(
                target_dir,
                dll_name,
                self.bundle.selected_variant(fsr4_variant),
                self.bundle.selected_backend(framegen_backend),
                appid=str(appid),
                game_name=game_info["name"],
                original_launch_options=original_options,
                previous_variant=existing_metadata.get("fsr4_variant"),
            )
            if result["status"] != "success":
                return result
            backend = result.get("framegen_backend") or self.bundle.selected_backend(framegen_backend)
            return {
                **result,
                "appid": str(appid),
                "name": game_info["name"],
                "dll_name": dll_name,
                "target_dir": str(target_dir),
                "launch_options": self.build_managed_launch_options(dll_name),
                "original_launch_options": original_options,
                "framegen_backend": backend,
                "message": f"Patched {game_info['name']} using {dll_name} with {result.get('fsr4_variant_label') or self.bundle.variant_info(fsr4_variant)['label']}.",
            }
        except Exception as exc:
            self._log(f"patch_game failed for {appid}: {exc}")
            return {"status": "error", "message": str(exc)}

    def unpatch_game(self, appid: str) -> dict:
        try:
            game_info = self.steam.game_record(str(appid))
            if not game_info:
                return {"status": "error", "message": "Game not found in Steam library."}
            install_root = Path(game_info["install_path"])
            if not install_root.exists():
                return {"status": "success", "appid": str(appid), "name": game_info["name"], "launch_options": "", "message": "Game install directory does not exist."}
            if self.steam.is_game_running(game_info):
                return {"status": "error", "message": "Close the game before unpatching."}
            marker = self._find_marker(install_root, str(appid))
            if not marker:
                return {"status": "success", "appid": str(appid), "name": game_info["name"], "launch_options": "", "message": "No Framegen patch found for this game."}
            metadata = self._read_marker(marker)
            target_dir = self._marker_target(marker, metadata)
            original_options = str(metadata.get("original_launch_options") or "")
            cleanup = self._unpatch_target(target_dir, marker)
            if cleanup["status"] != "success":
                return {**cleanup, "appid": str(appid), "name": game_info["name"]}
            self._log(f"unpatch_game success: appid={appid} target={target_dir}")
            return {
                "status": "success",
                "appid": str(appid),
                "name": game_info["name"],
                "launch_options": original_options,
                "message": f"Unpatched {game_info['name']}.",
            }
        except Exception as exc:
            self._log(f"unpatch_game failed for {appid}: {exc}")
            return {"status": "error", "message": str(exc)}

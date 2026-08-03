"""Management of the shared OptiScaler bundle in ``~/fgmod``."""

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import config
from .assets import (
    DEFAULT_FRAMEGEN_BACKEND,
    DEFAULT_FSR4_VARIANT,
    FRAMEGEN_BACKENDS,
    FSR4_DRIVER_OVERRIDE_FILENAME,
    FSR4_VARIANTS,
    FSR4_UPSCALER_FILENAME,
    INSTALL_MANIFEST_FILENAME,
    MANIFEST_SCHEMA_VERSION,
    OPTIPATCHER_ASSET,
    OPTISCALER_ARCHIVE_ASSET,
    OPTISCALER_PRE10_ASSET,
    AMDXC64_RDNA2_ASSET,
    FSR4_INT8_ASSET,
    FSR4_OFFICIAL_411_ASSET,
    FSR4_VALVE_411_ASSET,
    VERSION_FILENAME,
)
from .files import file_sha256, read_json, write_json


Logger = Callable[[str], None]


class BundleManager:
    def __init__(self, home: Path, plugin_dir: Path, logger: Logger):
        self.home = home
        self.plugin_dir = plugin_dir
        self.logger = logger

    @property
    def fgmod_path(self) -> Path:
        return self.home / "fgmod"

    def _log(self, message: str) -> None:
        self.logger(f"[Framegen] {message}")

    def _create_renamed_copies(self, source_file: Path, renames_dir: Path) -> bool:
        try:
            if not source_file.exists():
                self._log(f"Source file {source_file} does not exist")
                return False
            renames_dir.mkdir(parents=True, exist_ok=True)
            for filename in ("dxgi.dll", "winmm.dll", "dbghelp.dll", "version.dll", "wininet.dll", "winhttp.dll", "OptiScaler.asi"):
                shutil.copy2(source_file, renames_dir / filename)
            return True
        except OSError as exc:
            self._log(f"Failed to create renamed copies: {exc}")
            return False

    def _copy_launcher_scripts(self, assets_dir: Path, extract_path: Path) -> bool:
        try:
            scripts = {
                "fgmod.sh": "fgmod",
                "fgmod-uninstaller.sh": "fgmod-uninstaller.sh",
                "update-optiscaler-config.py": "update-optiscaler-config.py",
            }
            for source_name, destination_name in scripts.items():
                source = assets_dir / source_name
                if not source.exists():
                    continue
                destination = extract_path / destination_name
                shutil.copy2(source, destination)
                destination.chmod(0o755)
            return True
        except OSError as exc:
            self._log(f"Failed to copy launcher scripts: {exc}")
            return False

    def _extract_archive(self, archive_path: Path, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        environment = os.environ.copy()
        environment["LD_LIBRARY_PATH"] = ""
        result = subprocess.run(
            ["7z", "x", "-y", "-o" + str(output_dir), str(archive_path)],
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or f"Failed to extract {archive_path.name}")

    def _verify(self, path: Path, expected_sha256: str, description: str) -> str:
        actual = file_sha256(path)
        if actual.lower() != expected_sha256.lower():
            raise RuntimeError(f"{description} hash mismatch: expected {expected_sha256}, got {actual}")
        return actual

    def _manifest_path(self) -> Path:
        return self.fgmod_path / INSTALL_MANIFEST_FILENAME

    def load_manifest(self) -> dict:
        return read_json(self._manifest_path())

    @staticmethod
    def normalize_variant(value: str | None) -> str:
        return value if value in FSR4_VARIANTS else DEFAULT_FSR4_VARIANT

    @staticmethod
    def normalize_backend(value: str | None) -> str:
        return value if value in FRAMEGEN_BACKENDS else DEFAULT_FRAMEGEN_BACKEND

    def selected_variant(self, requested: str | None = None) -> str:
        if requested in FSR4_VARIANTS:
            return requested
        installed = self.load_manifest().get("selected_default_variant")
        return self.normalize_variant(installed)

    def selected_backend(self, requested: str | None = None) -> str:
        if requested in FRAMEGEN_BACKENDS:
            return requested
        manifest_backend = self.load_manifest().get("framegen_backend")
        if manifest_backend in FRAMEGEN_BACKENDS:
            return manifest_backend
        return self.normalize_backend(config.detect_backend(self.fgmod_path / "OptiScaler.ini"))

    def variant_info(self, variant: str | None) -> dict:
        return FSR4_VARIANTS[self.normalize_variant(variant)]

    def variant_dir(self, variant: str | None) -> Path:
        return self.fgmod_path / self.variant_info(variant)["dir_name"]

    def variant_path(self, variant: str | None) -> Path:
        return self.variant_dir(variant) / FSR4_UPSCALER_FILENAME

    def variant_extra_files(self, variant: str | None) -> list[dict]:
        return list(self.variant_info(variant).get("extra_files") or [])

    def variant_extra_path(self, variant: str | None, filename: str) -> Path:
        return self.variant_dir(variant) / filename

    def variant_injector_info(self, variant: str | None) -> dict | None:
        injector = self.variant_info(variant).get("injector")
        return injector if isinstance(injector, dict) else None

    def variant_injector_path(self, variant: str | None) -> Path | None:
        injector = self.variant_injector_info(variant)
        return self.variant_dir(variant) / injector["name"] if injector else None

    def variant_proxy_path(self, variant: str | None, dll_name: str) -> Path | None:
        if not self.variant_injector_info(variant):
            return None
        return self.variant_dir(variant) / "renames" / dll_name

    def variant_config_overrides(self, variant: str | None) -> dict:
        overrides = self.variant_info(variant).get("config_overrides") or {}
        return dict(overrides) if isinstance(overrides, dict) else {}

    def fgmod_version(self) -> str | None:
        manifest = self.load_manifest()
        optiscaler = manifest.get("optiscaler")
        if isinstance(optiscaler, dict) and optiscaler.get("version"):
            return str(optiscaler["version"])
        try:
            version = (self.fgmod_path / VERSION_FILENAME).read_text(encoding="utf-8").strip()
            return version or None
        except OSError:
            return None

    def managed_support_candidates(self, filename: str) -> list[Path]:
        candidates = [self.fgmod_path / filename]
        if filename == FSR4_UPSCALER_FILENAME:
            candidates = [self.fgmod_path / filename] + [self.variant_path(variant) for variant in FSR4_VARIANTS]
        else:
            for variant in FSR4_VARIANTS:
                if any(extra.get("name") == filename for extra in self.variant_extra_files(variant)):
                    candidates.append(self.variant_extra_path(variant, filename))
        unique: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            if str(candidate) not in seen:
                unique.append(candidate)
                seen.add(str(candidate))
        return unique

    def is_managed_support_file(self, path: Path) -> bool:
        return path.exists() and any(
            candidate.is_file() and file_sha256(path) == file_sha256(candidate)
            for candidate in self.managed_support_candidates(path.name)
        )

    def _sync_variant_root_extra_files(self, variant: str) -> None:
        selected = {extra["name"]: extra for extra in self.variant_extra_files(variant)}
        all_extra_names = {
            extra["name"]
            for item in FSR4_VARIANTS.values()
            for extra in item.get("extra_files", [])
        }
        for filename in all_extra_names:
            root_path = self.fgmod_path / filename
            if filename not in selected:
                if root_path.exists():
                    root_path.unlink()
                continue
            source = self.variant_extra_path(variant, filename)
            if not source.exists():
                raise FileNotFoundError(f"Prepared FSR4 variant extra file missing: {source}")
            shutil.copy2(source, root_path)

    def activate_variant(self, variant: str | None) -> str:
        variant_id = self.normalize_variant(variant)
        source = self.variant_path(variant_id)
        if not source.exists():
            raise FileNotFoundError(f"Prepared FSR4 variant missing: {source}")
        shutil.copy2(source, self.fgmod_path / FSR4_UPSCALER_FILENAME)
        self._sync_variant_root_extra_files(variant_id)
        return variant_id

    def detect_variant(self, directory: Path, upscaler_sha256: str | None) -> str | None:
        if not upscaler_sha256:
            return None
        normalized = upscaler_sha256.lower()
        for variant_id, variant in FSR4_VARIANTS.items():
            if str(variant.get("sha256", "")).lower() != normalized:
                continue
            if all(
                (directory / extra["name"]).exists()
                and file_sha256(directory / extra["name"]).lower() == extra["sha256"].lower()
                for extra in variant.get("extra_files", [])
            ):
                return variant_id
        return None

    def extract_static_optiscaler(
        self,
        selected_default_variant: str = DEFAULT_FSR4_VARIANT,
        framegen_backend: str = DEFAULT_FRAMEGEN_BACKEND,
    ) -> dict:
        """Prepare the shared bundle; replacement remains intentionally non-atomic for compatibility."""
        try:
            selected_default_variant = self.normalize_variant(selected_default_variant)
            framegen_backend = self.normalize_backend(framegen_backend)
            bin_path = self.plugin_dir / "bin"
            assets_dir = self.plugin_dir / "assets"
            if not bin_path.exists():
                return {"status": "error", "message": f"Bin directory not found: {bin_path}"}

            asset_sources = {
                "archive": (bin_path / OPTISCALER_ARCHIVE_ASSET["name"], OPTISCALER_ARCHIVE_ASSET),
                "int8": (bin_path / FSR4_INT8_ASSET["name"], FSR4_INT8_ASSET),
                "official": (bin_path / FSR4_OFFICIAL_411_ASSET["name"], FSR4_OFFICIAL_411_ASSET),
                "valve": (bin_path / FSR4_VALVE_411_ASSET["name"], FSR4_VALVE_411_ASSET),
                "amdxc64": (bin_path / AMDXC64_RDNA2_ASSET["name"], AMDXC64_RDNA2_ASSET),
                "pre10": (bin_path / OPTISCALER_PRE10_ASSET["name"], OPTISCALER_PRE10_ASSET),
                "optipatcher": (bin_path / OPTIPATCHER_ASSET["name"], OPTIPATCHER_ASSET),
            }
            for path, asset in asset_sources.values():
                if not path.exists():
                    return {"status": "error", "message": f"Required bundled asset missing: {asset['name']}"}
                self._verify(path, asset["sha256"], asset["name"])

            if self.fgmod_path.exists():
                shutil.rmtree(self.fgmod_path)
            self.fgmod_path.mkdir(parents=True, exist_ok=True)
            self._extract_archive(asset_sources["archive"][0], self.fgmod_path)

            source = self.fgmod_path / "OptiScaler.dll"
            if not self._create_renamed_copies(source, self.fgmod_path / "renames"):
                return {"status": "error", "message": "Failed to prepare renamed OptiScaler proxies."}
            if not self._copy_launcher_scripts(assets_dir, self.fgmod_path):
                return {"status": "error", "message": "Failed to copy launcher scripts."}

            plugins_dir = self.fgmod_path / "plugins"
            plugins_dir.mkdir(parents=True, exist_ok=True)
            optipatcher_dst = plugins_dir / "OptiPatcher.asi"
            shutil.copy2(asset_sources["optipatcher"][0], optipatcher_dst)
            optipatcher_sha256 = self._verify(optipatcher_dst, OPTIPATCHER_ASSET["sha256"], "Prepared OptiPatcher plugin")

            ini_file = self.fgmod_path / "OptiScaler.ini"
            config.configure(ini_file, framegen_backend, logger=self.logger)

            native_root = self.fgmod_path / FSR4_UPSCALER_FILENAME
            native_sha256 = self._verify(native_root, FSR4_VARIANTS["rdna4-native"]["sha256"], "Archive-native FSR4 upscaler")
            for variant_id in ("rdna4-native", "rdna34-official-411", "rdna2-valve-411-pre10"):
                variant_dir = self.variant_dir(variant_id)
                variant_dir.mkdir(parents=True, exist_ok=True)
                prepared = variant_dir / FSR4_UPSCALER_FILENAME
                shutil.copy2(native_root, prepared)
                self._verify(prepared, FSR4_VARIANTS[variant_id]["sha256"], f"Prepared {variant_id} FSR4 upscaler")

            official_dir = self.variant_dir("rdna34-official-411")
            shutil.copy2(asset_sources["official"][0], official_dir / FSR4_DRIVER_OVERRIDE_FILENAME)
            self._verify(official_dir / FSR4_DRIVER_OVERRIDE_FILENAME, FSR4_OFFICIAL_411_ASSET["sha256"], "Prepared official driver override")

            valve_dir = self.variant_dir("rdna2-valve-411-pre10")
            shutil.copy2(asset_sources["valve"][0], valve_dir / FSR4_DRIVER_OVERRIDE_FILENAME)
            shutil.copy2(asset_sources["amdxc64"][0], valve_dir / "amdxc64.dll")
            shutil.copy2(asset_sources["pre10"][0], valve_dir / "OptiScaler.dll")
            self._verify(valve_dir / FSR4_DRIVER_OVERRIDE_FILENAME, FSR4_VALVE_411_ASSET["sha256"], "Prepared Valve driver override")
            self._verify(valve_dir / "amdxc64.dll", AMDXC64_RDNA2_ASSET["sha256"], "Prepared RDNA2 driver override")
            self._verify(valve_dir / "OptiScaler.dll", OPTISCALER_PRE10_ASSET["sha256"], "Prepared pre10 OptiScaler injector")
            if not self._create_renamed_copies(valve_dir / "OptiScaler.dll", valve_dir / "renames"):
                return {"status": "error", "message": "Failed to prepare renamed pre10 OptiScaler proxies."}

            int8_dir = self.variant_dir("rdna23-int8")
            int8_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(asset_sources["int8"][0], int8_dir / FSR4_UPSCALER_FILENAME)
            self._verify(int8_dir / FSR4_UPSCALER_FILENAME, FSR4_INT8_ASSET["sha256"], "Prepared RDNA2-3 FSR4 upscaler")

            selected_default_variant = self.activate_variant(selected_default_variant)
            active_sha256 = file_sha256(self.fgmod_path / FSR4_UPSCALER_FILENAME)
            (self.fgmod_path / VERSION_FILENAME).write_text(OPTISCALER_ARCHIVE_ASSET["version"], encoding="utf-8")
            manifest = self._build_manifest(
                selected_default_variant,
                framegen_backend,
                native_sha256,
                optipatcher_sha256,
                active_sha256,
            )
            write_json(self._manifest_path(), manifest)
            return {
                "status": "success",
                "message": f"Successfully extracted OptiScaler {OPTISCALER_ARCHIVE_ASSET['version']} to ~/fgmod",
                "version": OPTISCALER_ARCHIVE_ASSET["version"],
                "selected_default_variant": selected_default_variant,
                "selected_default_variant_label": FSR4_VARIANTS[selected_default_variant]["label"],
                "framegen_backend": framegen_backend,
                "framegen_backend_label": FRAMEGEN_BACKENDS[framegen_backend],
            }
        except Exception as exc:
            self._log(f"Extract failed: {exc}")
            return {"status": "error", "message": f"Extract failed: {exc}"}

    def _build_manifest(
        self,
        selected_variant: str,
        framegen_backend: str,
        native_sha256: str,
        optipatcher_sha256: str,
        active_sha256: str,
    ) -> dict:
        variants = {}
        for variant_id, variant in FSR4_VARIANTS.items():
            injector = variant.get("injector")
            injector_manifest = None
            if isinstance(injector, dict):
                injector_manifest = {
                    key: injector[key]
                    for key in ("name", "sha256", "source_asset_name", "source_version")
                }
                injector_manifest["path"] = str(Path(variant["dir_name"]) / injector["name"])
            variants[variant_id] = {
                "label": variant["label"],
                "dir_name": variant["dir_name"],
                "path": str(Path(variant["dir_name"]) / FSR4_UPSCALER_FILENAME),
                "sha256": variant["sha256"],
                "source_asset_name": variant["source_asset_name"],
                "source_version": variant["source_version"],
                "uses_archive_native": bool(variant["uses_archive_native"]),
                "injector": injector_manifest,
                "config_overrides": dict(variant.get("config_overrides") or {}),
                "extra_files": [
                    {
                        **{key: extra[key] for key in ("name", "sha256", "source_asset_name", "source_version")},
                        "path": str(Path(variant["dir_name"]) / extra["name"]),
                    }
                    for extra in variant.get("extra_files", [])
                ],
            }
        return {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "optiscaler": {
                "asset_name": OPTISCALER_ARCHIVE_ASSET["name"],
                "version": OPTISCALER_ARCHIVE_ASSET["version"],
                "sha256": OPTISCALER_ARCHIVE_ASSET["sha256"],
                "native_upscaler_sha256": native_sha256,
            },
            "optipatcher": {
                "asset_name": OPTIPATCHER_ASSET["name"],
                "version": OPTIPATCHER_ASSET["version"],
                "sha256": optipatcher_sha256,
                "target_path": "plugins/OptiPatcher.asi",
            },
            "fsr4_variants": variants,
            "selected_default_variant": selected_variant,
            "framegen_backend": framegen_backend,
            "framegen_backend_label": FRAMEGEN_BACKENDS[framegen_backend],
            "active_root_upscaler": {
                "path": FSR4_UPSCALER_FILENAME,
                "sha256": active_sha256,
                "variant": selected_variant,
            },
        }

    def run_install(self, selected_variant: str, framegen_backend: str) -> dict:
        selected_variant = self.normalize_variant(selected_variant)
        framegen_backend = self.normalize_backend(framegen_backend)
        result = self.extract_static_optiscaler(selected_variant, framegen_backend)
        if result["status"] != "success":
            return {"status": "error", "message": f"OptiScaler extraction failed: {result.get('message', 'Unknown error')}"}
        return {
            "status": "success",
            "output": f"Successfully installed OptiScaler {result.get('version', OPTISCALER_ARCHIVE_ASSET['version'])} with {result.get('selected_default_variant_label', FSR4_VARIANTS[selected_variant]['label'])}.",
            "version": result.get("version", OPTISCALER_ARCHIVE_ASSET["version"]),
            "selected_default_variant": result.get("selected_default_variant", selected_variant),
            "selected_default_variant_label": result.get("selected_default_variant_label", FSR4_VARIANTS[selected_variant]["label"]),
            "framegen_backend": result.get("framegen_backend", framegen_backend),
            "framegen_backend_label": result.get("framegen_backend_label", FRAMEGEN_BACKENDS[framegen_backend]),
        }

    def uninstall(self) -> dict:
        try:
            if not self.fgmod_path.exists():
                return {"status": "success", "output": "No fgmod directory found to remove"}
            shutil.rmtree(self.fgmod_path)
            return {"status": "success", "output": "Successfully removed fgmod directory"}
        except OSError as exc:
            self._log(f"Uninstall error: {exc}")
            return {"status": "error", "message": f"Uninstall failed: {exc}", "output": str(exc)}

    def set_default_variant(self, selected_variant: str) -> dict:
        try:
            if not self.fgmod_path.exists():
                return {"status": "error", "message": "OptiScaler bundle not installed. Run Install first."}
            manifest = self.load_manifest()
            if not manifest:
                return {"status": "error", "message": "Install manifest missing. Reinstall OptiScaler."}
            selected_variant = self.activate_variant(selected_variant)
            active_sha256 = file_sha256(self.fgmod_path / FSR4_UPSCALER_FILENAME)
            manifest["selected_default_variant"] = selected_variant
            manifest["active_root_upscaler"] = {
                "path": FSR4_UPSCALER_FILENAME,
                "sha256": active_sha256,
                "variant": selected_variant,
            }
            manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
            write_json(self._manifest_path(), manifest)
            return {
                "status": "success",
                "output": f"Default FSR4 runtime switched to {FSR4_VARIANTS[selected_variant]['label']}.",
                "version": self.fgmod_version(),
                "selected_default_variant": selected_variant,
                "selected_default_variant_label": FSR4_VARIANTS[selected_variant]["label"],
            }
        except Exception as exc:
            self._log(f"Failed to switch default FSR4 runtime: {exc}")
            return {"status": "error", "message": f"Failed to switch default FSR4 runtime: {exc}"}

    def set_framegen_backend(self, framegen_backend: str) -> dict:
        try:
            if not self.fgmod_path.exists():
                return {"status": "error", "message": "OptiScaler bundle not installed. Run Install first."}
            backend = self.normalize_backend(framegen_backend)
            manifest = self.load_manifest()
            if not manifest:
                return {"status": "error", "message": "Install manifest missing. Reinstall OptiScaler."}
            ini_file = self.fgmod_path / "OptiScaler.ini"
            if not config.configure(ini_file, backend, logger=self.logger):
                return {"status": "error", "message": "Could not update the shared OptiScaler.ini."}
            manifest["framegen_backend"] = backend
            manifest["framegen_backend_label"] = FRAMEGEN_BACKENDS[backend]
            manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
            write_json(self._manifest_path(), manifest)
            return {
                "status": "success",
                "framegen_backend": backend,
                "framegen_backend_label": FRAMEGEN_BACKENDS[backend],
                "output": f"Frame generation backend set to {FRAMEGEN_BACKENDS[backend]}.",
            }
        except Exception as exc:
            self._log(f"Failed to set frame generation backend: {exc}")
            return {"status": "error", "message": f"Failed to set frame generation backend: {exc}"}

    def check(self) -> dict:
        required_files = [
            "OptiScaler.dll",
            "OptiScaler.ini",
            "dlssg_to_fsr3_amd_is_better.dll",
            "fakenvapi.dll",
            "fakenvapi.ini",
            "amd_fidelityfx_dx12.dll",
            "amd_fidelityfx_framegeneration_dx12.dll",
            FSR4_UPSCALER_FILENAME,
            "amd_fidelityfx_vk.dll",
            "libxess.dll",
            "libxess_dx11.dll",
            "libxess_fg.dll",
            "libxell.dll",
            "fgmod",
            "fgmod-uninstaller.sh",
            "update-optiscaler-config.py",
            INSTALL_MANIFEST_FILENAME,
        ]
        if not self.fgmod_path.exists() or any(not (self.fgmod_path / filename).exists() for filename in required_files):
            return {"exists": False}
        plugins_dir = self.fgmod_path / "plugins"
        if not (plugins_dir / "OptiPatcher.asi").exists():
            return {"exists": False}
        for variant_id, variant in FSR4_VARIANTS.items():
            variant_dir = self.variant_dir(variant_id)
            if not (variant_dir / FSR4_UPSCALER_FILENAME).exists():
                return {"exists": False}
            injector = variant.get("injector")
            if isinstance(injector, dict) and not (variant_dir / injector.get("name", "OptiScaler.dll")).exists():
                return {"exists": False}
            for extra in variant.get("extra_files", []):
                if not (variant_dir / extra["name"]).exists():
                    return {"exists": False}
        manifest = self.load_manifest()
        variant = self.selected_variant()
        backend = self.selected_backend()
        return {
            "exists": True,
            "version": self.fgmod_version(),
            "selected_fsr4_variant": variant,
            "selected_fsr4_variant_label": FSR4_VARIANTS[variant]["label"],
            "framegen_backend": backend,
            "framegen_backend_label": FRAMEGEN_BACKENDS[backend],
            "install_manifest_present": bool(manifest),
        }

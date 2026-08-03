"""Decky entry point for the Framegen plugin.

Decky-facing methods live here; filesystem, Steam, configuration, and patch
ownership concerns are implemented in focused service modules.
"""

from pathlib import Path

import decky

from services.assets import DEFAULT_FRAMEGEN_BACKEND, DEFAULT_FSR4_VARIANT
from services.bundle import BundleManager
from services.patcher import PatchManager
from services.steam import SteamLibrary


class Plugin:
    def __init__(self):
        home = Path(str(decky.HOME))
        plugin_dir = Path(str(decky.DECKY_PLUGIN_DIR))
        logger = decky.logger.error
        self._bundle = BundleManager(home, plugin_dir, logger)
        self._steam = SteamLibrary(home, logger)
        self._patcher = PatchManager(home, self._bundle, self._steam, logger)

    async def _main(self):
        decky.logger.info("Framegen plugin loaded")

    async def _unload(self):
        decky.logger.info("Framegen plugin unloaded.")

    async def extract_static_optiscaler(
        self,
        selected_default_variant: str = DEFAULT_FSR4_VARIANT,
        framegen_backend: str = DEFAULT_FRAMEGEN_BACKEND,
    ) -> dict:
        return self._bundle.extract_static_optiscaler(selected_default_variant, framegen_backend)

    async def run_install_fgmod(
        self,
        selected_default_variant: str = DEFAULT_FSR4_VARIANT,
        framegen_backend: str = DEFAULT_FRAMEGEN_BACKEND,
    ) -> dict:
        return self._bundle.run_install(selected_default_variant, framegen_backend)

    async def run_uninstall_fgmod(self) -> dict:
        return self._bundle.uninstall()

    async def set_default_fsr4_variant(self, selected_default_variant: str = DEFAULT_FSR4_VARIANT) -> dict:
        return self._bundle.set_default_variant(selected_default_variant)

    async def set_framegen_backend(self, framegen_backend: str = DEFAULT_FRAMEGEN_BACKEND) -> dict:
        return self._bundle.set_framegen_backend(framegen_backend)

    async def check_fgmod_path(self) -> dict:
        return self._bundle.check()

    async def list_installed_games(self) -> dict:
        return self._patcher.list_installed_games()

    async def get_path_defaults(self) -> dict:
        return {"home": str(self._steam.home), "steam_common": str(self._steam.steam_common_path())}

    async def log_error(self, error: str) -> None:
        decky.logger.error(f"FRONTEND: {error}")

    async def manual_patch_directory(
        self,
        directory: str,
        dll_name: str = "dxgi.dll",
        fsr4_variant: str = DEFAULT_FSR4_VARIANT,
        framegen_backend: str = DEFAULT_FRAMEGEN_BACKEND,
    ) -> dict:
        return self._patcher.manual_patch_directory(directory, dll_name, fsr4_variant, framegen_backend)

    async def manual_unpatch_directory(self, directory: str) -> dict:
        return self._patcher.manual_unpatch_directory(directory)

    async def get_game_status(self, appid: str) -> dict:
        return self._patcher.get_game_status(appid)

    async def patch_game(
        self,
        appid: str,
        dll_name: str = "dxgi.dll",
        current_launch_options: str = "",
        fsr4_variant: str = DEFAULT_FSR4_VARIANT,
        framegen_backend: str = DEFAULT_FRAMEGEN_BACKEND,
    ) -> dict:
        return self._patcher.patch_game(appid, dll_name, current_launch_options, fsr4_variant, framegen_backend)

    async def unpatch_game(self, appid: str) -> dict:
        return self._patcher.unpatch_game(appid)

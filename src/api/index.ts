import { callable } from "@decky/api";
import type { ApiResponse, GameConfigResponse } from "../types/index";

export const runInstallFGMod = callable<[], ApiResponse>("run_install_fgmod");

export const runUninstallFGMod = callable<[], ApiResponse>("run_uninstall_fgmod");

export const checkFGModPath = callable<[], { exists: boolean }>("check_fgmod_path");

export const listInstalledGames = callable<
  [],
  { status: string; games: { appid: string; name: string }[] }
>("list_installed_games");

export const cleanupManagedGame = callable<[string], ApiResponse>("cleanup_managed_game");

export const getGameConfig = callable<[string], GameConfigResponse>("get_game_config");

export const saveGameConfig = callable<
  [string, Record<string, string>, string | null, boolean, string | null],
  GameConfigResponse
>("save_game_config");

export const logError = callable<[string], void>("log_error");

export const getPathDefaults = callable<
  [],
  { home: string; steam_common?: string }
>("get_path_defaults");

export const runManualPatch = callable<[string], ApiResponse>("manual_patch_directory");

export const runManualUnpatch = callable<[string], ApiResponse>("manual_unpatch_directory");

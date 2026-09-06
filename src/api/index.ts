import { callable } from "@decky/api";

export const runInstallFGMod = callable<
  [selected_default_variant?: string],
  {
    status: string;
    message?: string;
    output?: string;
    version?: string;
    selected_default_variant?: string;
    selected_default_variant_label?: string;
  }
>("run_install_fgmod");

export const runUninstallFGMod = callable<
  [],
  { status: string; message?: string; output?: string }
>("run_uninstall_fgmod");

export const setDefaultFsr4Variant = callable<
  [selected_default_variant?: string],
  {
    status: string;
    message?: string;
    output?: string;
    version?: string;
    selected_default_variant?: string;
    selected_default_variant_label?: string;
  }
>("set_default_fsr4_variant");

export const checkFGModPath = callable<
  [],
  {
    exists: boolean;
    version?: string | null;
    selected_fsr4_variant?: string | null;
    selected_fsr4_variant_label?: string | null;
    install_manifest_present?: boolean;
    bundle_outdated?: boolean;
    outdated_variants?: string[];
    fsr4_watermark?: boolean;
  }
>("check_fgmod_path");

export const setFsr4Watermark = callable<
  [enabled: boolean],
  { status: string; message?: string; fsr4_watermark?: boolean }
>("set_fsr4_watermark");

export const listInstalledGames = callable<
  [],
  { status: string; message?: string; games: { appid: string; name: string; install_found?: boolean }[] }
>("list_installed_games");

export const logError = callable<[string], void>("log_error");

export const getPathDefaults = callable<
  [],
  { home: string; steam_common?: string }
>("get_path_defaults");

export const runManualPatch = callable<
  [string, string, string],
  {
    status: string;
    message?: string;
    output?: string;
    fsr4_variant?: string;
    fsr4_variant_label?: string;
    fsr4_upscaler_sha256?: string;
    optiscaler_version?: string | null;
  }
>("manual_patch_directory");

export const runManualUnpatch = callable<
  [string],
  { status: string; message?: string; output?: string }
>("manual_unpatch_directory");

export const getGameStatus = callable<
  [appid: string],
  {
    status: string;
    message?: string;
    appid?: string;
    name?: string;
    install_found?: boolean;
    patched?: boolean;
    dll_name?: string | null;
    target_dir?: string | null;
    patched_at?: string | null;
    optiscaler_version?: string | null;
    fsr4_variant?: string | null;
    fsr4_variant_label?: string | null;
    fsr4_upscaler_sha256?: string | null;
    injector_outdated?: boolean;
    game_options?: { dx12_upscaler?: string; frame_generation?: string };
    ini_dx12_upscaler?: string | null;
    ini_fg_input?: string | null;
  }
>("get_game_status");

export const getGameDiagnostics = callable<
  [appid: string],
  { status: string; message?: string; report?: string; path?: string }
>("get_game_diagnostics");

export const patchGame = callable<
  [appid: string, dll_name: string, current_launch_options: string, fsr4_variant: string, dx12_upscaler: string, frame_generation: string],
  {
    status: string;
    message?: string;
    appid?: string;
    name?: string;
    dll_name?: string;
    target_dir?: string;
    launch_options?: string;
    original_launch_options?: string;
    optiscaler_version?: string | null;
    fsr4_variant?: string;
    fsr4_variant_label?: string;
    fsr4_upscaler_sha256?: string;
  }
>("patch_game");

export const unpatchGame = callable<
  [appid: string],
  {
    status: string;
    message?: string;
    appid?: string;
    name?: string;
    launch_options?: string;
  }
>("unpatch_game");

import { callable } from "@decky/api";

export const runInstallFGMod = callable<
  [],
  { status: string; message?: string; output?: string }
>("run_install_fgmod");

export const runUninstallFGMod = callable<
  [],
  { status: string; message?: string; output?: string }
>("run_uninstall_fgmod");

export const checkFGModPath = callable<
  [],
  { exists: boolean }
>("check_fgmod_path");

export const listInstalledGames = callable<
  [],
  { status: string; games: { appid: string; name: string }[] }
>("list_installed_games");

export const logError = callable<[string], void>("log_error");

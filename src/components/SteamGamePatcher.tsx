import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ButtonItem, DropdownItem, Field, PanelSectionRow, useQuickAccessVisible } from "@decky/ui";
import { toaster } from "@decky/api";
import { listInstalledGames, getGameStatus, getGameDiagnostics, patchGame, unpatchGame } from "../api";
import { FSR4_VARIANT_OPTIONS, DX12_UPSCALER_OPTIONS, FRAME_GENERATION_OPTIONS } from "../utils/constants";
import { copyTextToClipboard } from "../utils";

// ─── SteamClient helpers ─────────────────────────────────────────────────────

const getAppLaunchOptions = (appId: number): Promise<string> =>
  new Promise((resolve, reject) => {
    if (typeof SteamClient === "undefined" || !SteamClient?.Apps?.RegisterForAppDetails) {
      resolve("");
      return;
    }
    let settled = false;
    let unregister = () => {};
    const timeout = window.setTimeout(() => {
      if (settled) return;
      settled = true;
      unregister();
      reject(new Error("Timed out reading launch options."));
    }, 5000);
    const registration = SteamClient.Apps.RegisterForAppDetails(
      appId,
      (details: { strLaunchOptions?: string }) => {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeout);
        unregister();
        resolve(details?.strLaunchOptions ?? "");
      }
    );
    unregister = registration.unregister;
  });

const setAppLaunchOptions = (appId: number, options: string): void => {
  if (typeof SteamClient !== "undefined" && SteamClient?.Apps?.SetAppLaunchOptions) {
    SteamClient.Apps.SetAppLaunchOptions(appId, options);
  }
};

// ─── Types ───────────────────────────────────────────────────────────────────

type GameEntry = { appid: string; name: string; install_found?: boolean };

type GameStatus = {
  status: "success" | "error";
  message?: string;
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
};

// ─── Module-level state persistence ──────────────────────────────────────────

let lastSelectedAppId = "";

// ─── Component ───────────────────────────────────────────────────────────────

interface SteamGamePatcherProps {
  dllName: string;
  fsr4Variant: string;
}

export function SteamGamePatcher({ dllName, fsr4Variant }: SteamGamePatcherProps) {
  const [games, setGames] = useState<GameEntry[]>([]);
  const [gamesLoading, setGamesLoading] = useState(true);
  const [selectedAppId, setSelectedAppId] = useState<string>(() => lastSelectedAppId);
  const [gameStatus, setGameStatus] = useState<GameStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [busyAction, setBusyAction] = useState<"patch" | "unpatch" | "diagnostics" | null>(null);
  const [resultMessage, setResultMessage] = useState<string>("");
  // Per-game choices. They follow the global default / the patched game's marker
  // until the user touches them for the selected game.
  const [gameVariant, setGameVariant] = useState<string>(fsr4Variant);
  const [upscalerChoice, setUpscalerChoice] = useState<string>("auto");
  const [fgChoice, setFgChoice] = useState<string>("default");
  const touchedAppId = useRef<string>("");

  // ── Data loaders ───────────────────────────────────────────────────────────

  const gamesLoadedOnce = useRef(false);
  const qamVisible = useQuickAccessVisible();

  // `silent` refreshes keep the current list on screen (no "Loading games..."
  // flash) and never toast: they run every time the Quick Access Menu opens so
  // games installed or removed since the plugin mounted show up.
  const loadGames = useCallback(async (silent = false) => {
    if (!silent) setGamesLoading(true);
    try {
      const result = await listInstalledGames();
      if (result.status !== "success") throw new Error(result.message || "Failed to load games.");
      const gameList = result.games as GameEntry[];
      gamesLoadedOnce.current = true;
      setGames(gameList);
      if (!gameList.length) {
        lastSelectedAppId = "";
        setSelectedAppId("");
        return;
      }
      setSelectedAppId((current) => {
        const valid =
          current && gameList.some((g) => g.appid === current) ? current : gameList[0].appid;
        lastSelectedAppId = valid;
        return valid;
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load games.";
      if (silent) {
        console.warn("[Framegen] silent game-list refresh failed:", msg);
        return;
      }
      toaster.toast({ title: "Decky Framegen", body: msg });
    } finally {
      if (!silent) setGamesLoading(false);
    }
  }, []);

  const loadStatus = useCallback(async (appid: string) => {
    if (!appid) {
      setGameStatus(null);
      return;
    }
    setStatusLoading(true);
    try {
      const result = await getGameStatus(appid);
      setGameStatus(result as GameStatus);
    } catch (err) {
      setGameStatus({
        status: "error",
        message: err instanceof Error ? err.message : "Failed to load status.",
      });
    } finally {
      setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!qamVisible) return;
    void loadGames(gamesLoadedOnce.current);
  }, [qamVisible, loadGames]);

  useEffect(() => {
    if (!selectedAppId) {
      setGameStatus(null);
      return;
    }
    void loadStatus(selectedAppId);
  }, [selectedAppId, loadStatus]);

  // Initialise the per-game controls from the marker (patched game) or the global
  // default (unpatched game) whenever the selection or the status changes, unless
  // the user already changed them for this very game.
  useEffect(() => {
    if (touchedAppId.current === selectedAppId) return;
    if (gameStatus?.patched) {
      setGameVariant(gameStatus.fsr4_variant || fsr4Variant);
      setUpscalerChoice(gameStatus.game_options?.dx12_upscaler || "auto");
      setFgChoice(gameStatus.game_options?.frame_generation || "default");
    } else {
      setGameVariant(fsr4Variant);
      setUpscalerChoice("auto");
      setFgChoice("default");
    }
  }, [selectedAppId, gameStatus, fsr4Variant]);

  const markTouched = () => {
    touchedAppId.current = selectedAppId;
  };

  // ── Derived state ──────────────────────────────────────────────────────────

  const selectedGame = useMemo(
    () => games.find((g) => g.appid === selectedAppId) ?? null,
    [games, selectedAppId]
  );

  const selectedVariantLabel = useMemo(
    () => FSR4_VARIANT_OPTIONS.find((option) => option.value === gameVariant)?.label ?? gameVariant,
    [gameVariant]
  );

  const isPatchedWithDifferentDll =
    gameStatus?.patched && gameStatus?.dll_name && gameStatus.dll_name !== dllName;

  // The game keeps the runtime it was patched with; pressing Reinstall re-patches
  // it with the currently selected default.
  const isPatchedWithDifferentVariant = Boolean(
    gameStatus?.patched && gameStatus?.fsr4_variant && gameStatus.fsr4_variant !== gameVariant
  );
  const optionsChanged = Boolean(
    gameStatus?.patched &&
      ((gameStatus.game_options?.dx12_upscaler || "auto") !== upscalerChoice ||
        (gameStatus.game_options?.frame_generation || "default") !== fgChoice)
  );

  const canPatch = Boolean(selectedGame && gameStatus?.install_found && !busyAction);
  const canUnpatch = Boolean(selectedGame && gameStatus?.patched && !busyAction);

  const patchButtonLabel = useMemo(() => {
    if (busyAction === "patch") return "Patching...";
    if (!selectedGame) return "Patch this game";
    if (!gameStatus?.install_found) return "Install not found";
    if (isPatchedWithDifferentDll) return `Switch to ${dllName}`;
    if (gameStatus?.patched) return (isPatchedWithDifferentVariant || optionsChanged) ? `Reinstall (${dllName}) — apply changes` : `Reinstall (${dllName})`;
    return `Patch with ${dllName}`;
  }, [busyAction, dllName, gameStatus, isPatchedWithDifferentDll, isPatchedWithDifferentVariant, optionsChanged, selectedGame]);

  // ── Actions ────────────────────────────────────────────────────────────────

  const handlePatch = useCallback(async () => {
    if (!selectedGame || !selectedAppId || busyAction) return;
    setBusyAction("patch");
    setResultMessage("");
    try {
      let currentLaunchOptions = "";
      try {
        currentLaunchOptions = await getAppLaunchOptions(Number(selectedAppId));
      } catch {
        // Patching with "" would record an empty original and a later unpatch
        // would wipe the user's own launch options, so stop here instead.
        throw new Error("Could not read this game's current launch options from Steam. Please try again.");
      }
      const result = await patchGame(selectedAppId, dllName, currentLaunchOptions, gameVariant, upscalerChoice, fgChoice);
      touchedAppId.current = "";
      if (result.status !== "success") throw new Error(result.message || "Patch failed.");
      setAppLaunchOptions(Number(selectedAppId), result.launch_options || "");
      const msg = result.message || `Patched ${selectedGame.name}.`;
      setResultMessage(msg);
      toaster.toast({ title: "Decky Framegen", body: msg });
      await loadStatus(selectedAppId);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Patch failed.";
      setResultMessage(`Error: ${msg}`);
      toaster.toast({ title: "Decky Framegen", body: msg });
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, dllName, gameVariant, upscalerChoice, fgChoice, loadStatus, selectedAppId, selectedGame]);

  const handleUnpatch = useCallback(async () => {
    if (!selectedGame || !selectedAppId || busyAction) return;
    setBusyAction("unpatch");
    setResultMessage("");
    try {
      const result = await unpatchGame(selectedAppId);
      if (result.status !== "success") throw new Error(result.message || "Unpatch failed.");
      setAppLaunchOptions(Number(selectedAppId), result.launch_options || "");
      const msg = result.message || `Unpatched ${selectedGame.name}.`;
      setResultMessage(msg);
      toaster.toast({ title: "Decky Framegen", body: msg });
      await loadStatus(selectedAppId);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unpatch failed.";
      setResultMessage(`Error: ${msg}`);
      toaster.toast({ title: "Decky Framegen", body: msg });
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, loadStatus, selectedAppId, selectedGame]);

  const handleDiagnostics = useCallback(async () => {
    if (!selectedAppId || busyAction) return;
    setBusyAction("diagnostics");
    try {
      const result = await getGameDiagnostics(selectedAppId);
      if (result.status !== "success" || !result.report) throw new Error(result.message || "Could not collect diagnostics.");
      const copied = await copyTextToClipboard(result.report);
      const where = result.path ? ` Also saved to ${result.path}.` : "";
      toaster.toast({
        title: "Decky Framegen",
        body: copied ? `Diagnostics copied to the clipboard.${where}` : `Clipboard unavailable.${where}`,
      });
    } catch (err) {
      toaster.toast({ title: "Decky Framegen", body: err instanceof Error ? err.message : "Could not collect diagnostics." });
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, selectedAppId]);

  // ── Status display ─────────────────────────────────────────────────────────

  const statusDisplay = useMemo(() => {
    if (!selectedGame) return { text: "—", color: undefined as string | undefined };
    if (statusLoading) return { text: "Loading...", color: undefined };
    if (!gameStatus || gameStatus.status === "error")
      return { text: gameStatus?.message || "—", color: undefined };
    if (!gameStatus.install_found) return { text: "Install not found", color: "#ffd866" };
    if (!gameStatus.patched) return { text: "Not patched", color: undefined };
    const dllLabel = gameStatus.dll_name || "unknown";
    if (gameStatus.injector_outdated)
      return { text: `Patched (${dllLabel}) — old injector, press Reinstall`, color: "#ffd866" };
    if (isPatchedWithDifferentDll)
      return { text: `Patched (${dllLabel}) — switch available`, color: "#ffd866" };
    return { text: `Patched (${dllLabel})`, color: "#3fb950" };
  }, [gameStatus, isPatchedWithDifferentDll, selectedGame, statusLoading]);

  const focusableFieldProps = { focusable: true, highlightOnFocus: true } as const;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <>
      <PanelSectionRow>
        <DropdownItem
          layout="below"
          label="Steam game"
          menuLabel="Select a Steam game"
          strDefaultLabel={gamesLoading ? "Loading games..." : games.length === 0 ? "No Steam games found" : "Choose a game"}
          disabled={gamesLoading || games.length === 0}
          selectedOption={selectedAppId}
          rgOptions={games.map((g) => ({
            data: g.appid,
            label: g.install_found === false ? `${g.name} (not installed)` : g.name,
          }))}
          onChange={(option) => {
            const next = String(option.data);
            lastSelectedAppId = next;
            setSelectedAppId(next);
            setResultMessage("");
          }}
        />
      </PanelSectionRow>

      {selectedGame && (
        <>
          <PanelSectionRow>
            <Field {...focusableFieldProps} label="Patch status">
              {statusDisplay.color ? (
                <span style={{ color: statusDisplay.color, fontWeight: 600 }}>
                  {statusDisplay.text}
                </span>
              ) : (
                statusDisplay.text
              )}
            </Field>
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              layout="below"
              label="Runtime for this game"
              description={
                gameStatus?.patched
                  ? isPatchedWithDifferentVariant
                    ? `Currently ${gameStatus?.fsr4_variant_label || "unknown"}. Press Reinstall to switch.`
                    : `Currently ${gameStatus?.fsr4_variant_label || "unknown"}.`
                  : `Will patch with ${selectedVariantLabel}.`
              }
              menuLabel="Runtime for this game"
              selectedOption={gameVariant}
              rgOptions={FSR4_VARIANT_OPTIONS.map((option) => ({ data: option.value, label: option.label }))}
              disabled={busyAction !== null}
              onChange={(option) => {
                markTouched();
                setGameVariant(String(option.data));
              }}
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              layout="below"
              label="DX12 upscaler"
              description={
                gameStatus?.patched && gameStatus.ini_dx12_upscaler
                  ? `INI currently: ${gameStatus.ini_dx12_upscaler}${optionsChanged ? " — press Reinstall to apply" : ""}`
                  : "Written to OptiScaler.ini when you Patch/Reinstall. 'Runtime default' keeps FSR 3.1 → FSR 4 unless you chose something in the overlay."
              }
              menuLabel="DX12 upscaler"
              selectedOption={upscalerChoice}
              rgOptions={DX12_UPSCALER_OPTIONS.map((option) => ({ data: option.value, label: option.label }))}
              disabled={busyAction !== null}
              onChange={(option) => {
                markTouched();
                setUpscalerChoice(String(option.data));
              }}
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              layout="below"
              label="Frame generation"
              description={
                fgChoice === "optifg"
                  ? "OptiScaler generates frames from the upscaler. Game dependent; UI can glitch. Enable it in the Insert overlay if it stays off."
                  : gameStatus?.patched && gameStatus.ini_fg_input
                    ? `INI currently: FGInput=${gameStatus.ini_fg_input}${optionsChanged ? " — press Reinstall to apply" : ""}`
                    : "Uses the game's own DLSS Frame Generation toggle through Nukem's mod."
              }
              menuLabel="Frame generation"
              selectedOption={fgChoice}
              rgOptions={FRAME_GENERATION_OPTIONS.map((option) => ({ data: option.value, label: option.label }))}
              disabled={busyAction !== null}
              onChange={(option) => {
                markTouched();
                setFgChoice(String(option.data));
              }}
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <ButtonItem layout="below" disabled={!canPatch} onClick={handlePatch}>
              {patchButtonLabel}
            </ButtonItem>
          </PanelSectionRow>

          {canUnpatch && (
            <PanelSectionRow>
              <ButtonItem
                layout="below"
                disabled={busyAction !== null}
                onClick={handleUnpatch}
              >
                {busyAction === "unpatch" ? "Unpatching..." : "Unpatch this game"}
              </ButtonItem>
            </PanelSectionRow>
          )}

          <PanelSectionRow>
            <ButtonItem
              layout="below"
              disabled={!selectedAppId || busyAction !== null || statusLoading}
              onClick={() => void loadStatus(selectedAppId)}
            >
              {statusLoading ? "Refreshing..." : "Refresh status"}
            </ButtonItem>
          </PanelSectionRow>

          <PanelSectionRow>
            <ButtonItem
              layout="below"
              disabled={!selectedAppId || busyAction !== null}
              onClick={handleDiagnostics}
              description="Copies bundle state, marker, INI keys and the telling OptiScaler.log lines to the clipboard."
            >
              {busyAction === "diagnostics" ? "Collecting..." : "Copy diagnostics"}
            </ButtonItem>
          </PanelSectionRow>

          {resultMessage && (
            <PanelSectionRow>
              <Field {...focusableFieldProps} label="Result">
                {resultMessage}
              </Field>
            </PanelSectionRow>
          )}
        </>
      )}
    </>
  );
}

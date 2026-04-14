import { useCallback, useEffect, useMemo, useState } from "react";
import { ButtonItem, DropdownItem, Field, PanelSectionRow } from "@decky/ui";
import { toaster } from "@decky/api";
import { listInstalledGames, getGameStatus, patchGame, unpatchGame } from "../api";

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
};

// ─── Module-level state persistence ──────────────────────────────────────────

let lastSelectedAppId = "";

// ─── Component ───────────────────────────────────────────────────────────────

interface SteamGamePatcherProps {
  dllName: string;
}

export function SteamGamePatcher({ dllName }: SteamGamePatcherProps) {
  const [games, setGames] = useState<GameEntry[]>([]);
  const [gamesLoading, setGamesLoading] = useState(true);
  const [selectedAppId, setSelectedAppId] = useState<string>(() => lastSelectedAppId);
  const [gameStatus, setGameStatus] = useState<GameStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [busyAction, setBusyAction] = useState<"patch" | "unpatch" | null>(null);
  const [resultMessage, setResultMessage] = useState<string>("");

  // ── Data loaders ───────────────────────────────────────────────────────────

  const loadGames = useCallback(async () => {
    setGamesLoading(true);
    try {
      const result = await listInstalledGames();
      if (result.status !== "success") throw new Error(result.message || "Failed to load games.");
      const gameList = result.games as GameEntry[];
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
      toaster.toast({ title: "Decky Framegen", body: msg });
    } finally {
      setGamesLoading(false);
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
    void loadGames();
  }, [loadGames]);

  useEffect(() => {
    if (!selectedAppId) {
      setGameStatus(null);
      return;
    }
    void loadStatus(selectedAppId);
  }, [selectedAppId, loadStatus]);

  // ── Derived state ──────────────────────────────────────────────────────────

  const selectedGame = useMemo(
    () => games.find((g) => g.appid === selectedAppId) ?? null,
    [games, selectedAppId]
  );

  const isPatchedWithDifferentDll =
    gameStatus?.patched && gameStatus?.dll_name && gameStatus.dll_name !== dllName;

  const canPatch = Boolean(selectedGame && gameStatus?.install_found && !busyAction);
  const canUnpatch = Boolean(selectedGame && gameStatus?.patched && !busyAction);

  const patchButtonLabel = useMemo(() => {
    if (busyAction === "patch") return "Patching...";
    if (!selectedGame) return "Patch this game";
    if (!gameStatus?.install_found) return "Install not found";
    if (isPatchedWithDifferentDll) return `Switch to ${dllName}`;
    if (gameStatus?.patched) return `Reinstall (${dllName})`;
    return `Patch with ${dllName}`;
  }, [busyAction, dllName, gameStatus, isPatchedWithDifferentDll, selectedGame]);

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
        // non-fatal: proceed without current launch options
      }
      const result = await patchGame(selectedAppId, dllName, currentLaunchOptions);
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
  }, [busyAction, dllName, loadStatus, selectedAppId, selectedGame]);

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

  // ── Status display ─────────────────────────────────────────────────────────

  const statusDisplay = useMemo(() => {
    if (!selectedGame) return { text: "—", color: undefined as string | undefined };
    if (statusLoading) return { text: "Loading...", color: undefined };
    if (!gameStatus || gameStatus.status === "error")
      return { text: gameStatus?.message || "—", color: undefined };
    if (!gameStatus.install_found) return { text: "Install not found", color: "#ffd866" };
    if (!gameStatus.patched) return { text: "Not patched", color: undefined };
    const dllLabel = gameStatus.dll_name || "unknown";
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
          label="Steam game"
          menuLabel="Select a Steam game"
          strDefaultLabel={gamesLoading ? "Loading games..." : "Choose a game"}
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

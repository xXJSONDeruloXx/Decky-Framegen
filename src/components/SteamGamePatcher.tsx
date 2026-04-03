import { useCallback, useEffect, useMemo, useState } from "react";
import { ButtonItem, DropdownItem, Field, PanelSectionRow } from "@decky/ui";
import { listInstalledGames } from "../api";
import { createAutoCleanupTimer } from "../utils";
import { TIMEOUTS } from "../utils/constants";

// ─── SteamClient helpers ─────────────────────────────────────────────────────

/**
 * Wrap the callback-based RegisterForAppDetails in a Promise.
 * Resolves with the current launch options string, or "" if SteamClient is
 * unavailable (e.g. desktop / dev mode).  Times out after 5 seconds.
 */
const getSteamLaunchOptions = (appId: number): Promise<string> =>
  new Promise((resolve, reject) => {
    if (
      typeof SteamClient === "undefined" ||
      !SteamClient?.Apps?.RegisterForAppDetails
    ) {
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

const setSteamLaunchOptions = (appId: number, options: string): void => {
  if (
    typeof SteamClient === "undefined" ||
    !SteamClient?.Apps?.SetAppLaunchOptions
  ) {
    throw new Error("SteamClient.Apps.SetAppLaunchOptions is not available.");
  }
  SteamClient.Apps.SetAppLaunchOptions(appId, options);
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Remove any fgmod invocation from a launch options string, keeping the rest. */
const stripFgmod = (opts: string): string =>
  opts
    .replace(/DLL=\S+\s+~\/fgmod\/fgmod\s+%command%/g, "")
    .replace(/~\/fgmod\/fgmod\s+%command%/g, "")
    .trim();

/** Extract the DLL= value from a launch options string, if present. */
const extractDllName = (opts: string): string | null => {
  const m = opts.match(/DLL=(\S+)\s+~\/fgmod\/fgmod/);
  return m ? m[1] : null;
};

// ─── Component ───────────────────────────────────────────────────────────────

interface SteamGamePatcherProps {
  dllName: string;
}

type GameEntry = { appid: string; name: string };

export function SteamGamePatcher({ dllName }: SteamGamePatcherProps) {
  const [games, setGames] = useState<GameEntry[]>([]);
  const [gamesLoading, setGamesLoading] = useState(true);
  const [selectedAppId, setSelectedAppId] = useState<string>("");
  const [launchOptions, setLaunchOptions] = useState<string>("");
  const [launchOptionsLoading, setLaunchOptionsLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [resultMessage, setResultMessage] = useState<string>("");

  // Auto-clear result message
  useEffect(() => {
    if (resultMessage) {
      return createAutoCleanupTimer(
        () => setResultMessage(""),
        TIMEOUTS.resultDisplay
      );
    }
    return undefined;
  }, [resultMessage]);

  // Load game list on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setGamesLoading(true);
      try {
        const result = await listInstalledGames();
        if (cancelled) return;
        if (result.status === "success" && result.games.length > 0) {
          setGames(result.games);
          setSelectedAppId(result.games[0].appid);
        }
      } catch (e) {
        console.error("SteamGamePatcher: failed to load games", e);
      } finally {
        if (!cancelled) setGamesLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Reload launch options when selected game changes
  useEffect(() => {
    if (!selectedAppId) {
      setLaunchOptions("");
      return;
    }
    let cancelled = false;
    (async () => {
      setLaunchOptionsLoading(true);
      try {
        const opts = await getSteamLaunchOptions(Number(selectedAppId));
        if (!cancelled) setLaunchOptions(opts);
      } catch {
        if (!cancelled) setLaunchOptions("");
      } finally {
        if (!cancelled) setLaunchOptionsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedAppId]);

  const targetCommand = `DLL=${dllName} ~/fgmod/fgmod %command%`;
  const isManaged = launchOptions.includes("fgmod/fgmod");
  const activeDll = useMemo(() => extractDllName(launchOptions), [launchOptions]);
  const selectedGame = useMemo(
    () => games.find((g) => g.appid === selectedAppId) ?? null,
    [games, selectedAppId]
  );

  const handleSet = useCallback(() => {
    if (!selectedAppId || busy) return;
    setBusy(true);
    try {
      setSteamLaunchOptions(Number(selectedAppId), targetCommand);
      setLaunchOptions(targetCommand);
      setResultMessage(
        `✅ Launch options set for ${selectedGame?.name ?? selectedAppId}`
      );
    } catch (e) {
      setResultMessage(`❌ ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
    }
  }, [selectedAppId, targetCommand, selectedGame, busy]);

  const handleRemove = useCallback(() => {
    if (!selectedAppId || busy) return;
    setBusy(true);
    try {
      const stripped = stripFgmod(launchOptions);
      setSteamLaunchOptions(Number(selectedAppId), stripped);
      setLaunchOptions(stripped);
      setResultMessage(
        `✅ Removed fgmod from ${selectedGame?.name ?? selectedAppId}`
      );
    } catch (e) {
      setResultMessage(`❌ ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
    }
  }, [selectedAppId, launchOptions, selectedGame, busy]);

  // ── Status display ──────────────────────────────────────────────────────────
  const statusText = useMemo(() => {
    if (!selectedGame) return "—";
    if (launchOptionsLoading) return "Loading...";
    if (!isManaged) return "Not set";
    if (activeDll && activeDll !== dllName)
      return `Active — ${activeDll} · switch to apply ${dllName}`;
    return `Active — ${activeDll ?? dllName}`;
  }, [selectedGame, launchOptionsLoading, isManaged, activeDll, dllName]);

  const statusColor = useMemo(() => {
    if (!isManaged || launchOptionsLoading) return undefined;
    if (activeDll && activeDll !== dllName) return "#ffd866"; // yellow — different DLL selected
    return "#3fb950"; // green — active and matching
  }, [isManaged, launchOptionsLoading, activeDll, dllName]);

  const setButtonLabel = useMemo(() => {
    if (busy) return "Applying...";
    if (!isManaged) return "Enable for this game";
    if (activeDll && activeDll !== dllName) return `Switch to ${dllName}`;
    return "Re-apply";
  }, [busy, isManaged, activeDll, dllName]);

  return (
    <>
      <PanelSectionRow>
        <DropdownItem
          label="Steam game"
          menuLabel="Select a Steam game"
          strDefaultLabel={
            gamesLoading ? "Loading games..." : "Choose a game"
          }
          disabled={gamesLoading || games.length === 0}
          selectedOption={selectedAppId}
          rgOptions={games.map((g) => ({ data: g.appid, label: g.name }))}
          onChange={(option) => {
            setSelectedAppId(String(option.data));
            setResultMessage("");
          }}
        />
      </PanelSectionRow>

      {selectedGame && (
        <>
          <PanelSectionRow>
            <Field focusable label="Launch options status">
              {statusColor ? (
                <span style={{ color: statusColor, fontWeight: 600 }}>
                  {statusText}
                </span>
              ) : (
                statusText
              )}
            </Field>
          </PanelSectionRow>

          <PanelSectionRow>
            <ButtonItem
              layout="below"
              disabled={busy || launchOptionsLoading}
              onClick={handleSet}
            >
              {setButtonLabel}
            </ButtonItem>
          </PanelSectionRow>

          {isManaged && (
            <PanelSectionRow>
              <ButtonItem
                layout="below"
                disabled={busy}
                onClick={handleRemove}
              >
                {busy ? "Removing..." : "Remove from launch options"}
              </ButtonItem>
            </PanelSectionRow>
          )}

          {resultMessage && (
            <PanelSectionRow>
              <Field focusable label="Result">
                {resultMessage}
              </Field>
            </PanelSectionRow>
          )}
        </>
      )}
    </>
  );
}

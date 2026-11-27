import { useCallback, useEffect, useMemo, useState } from "react";
import { ButtonItem, DropdownItem, Field, PanelSectionRow } from "@decky/ui";
import { toaster } from "@decky/api";
import { listInstalledGames, getGameStatus, patchGame, unpatchGame } from "../api";
import { FSR4_VARIANT_OPTIONS } from "../utils/constants";
import { L } from "../utils/i18n";

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
      reject(new Error(L("Timed out reading launch options.", "讀取啟動選項逾時。")));
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
  const [busyAction, setBusyAction] = useState<"patch" | "unpatch" | null>(null);
  const [resultMessage, setResultMessage] = useState<string>("");

  // ── Data loaders ───────────────────────────────────────────────────────────

  const loadGames = useCallback(async () => {
    setGamesLoading(true);
    try {
      const result = await listInstalledGames();
      if (result.status !== "success") throw new Error(result.message || L("Failed to load games.", "無法載入遊戲。"));
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
      const msg = err instanceof Error ? err.message : L("Failed to load games.", "無法載入遊戲。");
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
        message: err instanceof Error ? err.message : L("Failed to load status.", "無法載入狀態。"),
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

  const selectedVariantLabel = useMemo(
    () => FSR4_VARIANT_OPTIONS.find((option) => option.value === fsr4Variant)?.label ?? fsr4Variant,
    [fsr4Variant]
  );

  const isPatchedWithDifferentDll =
    gameStatus?.patched && gameStatus?.dll_name && gameStatus.dll_name !== dllName;

  const canPatch = Boolean(selectedGame && gameStatus?.install_found && !busyAction);
  const canUnpatch = Boolean(selectedGame && gameStatus?.patched && !busyAction);

  const patchButtonLabel = useMemo(() => {
    if (busyAction === "patch") return L("Patching...", "正在套用修補...");
    if (!selectedGame) return L("Patch this game", "修補此遊戲");
    if (!gameStatus?.install_found) return L("Install not found", "找不到遊戲安裝路徑");
    if (isPatchedWithDifferentDll) return L(`Switch to ${dllName}`, `切換為 ${dllName}`);
    if (gameStatus?.patched) return L(`Reinstall (${dllName})`, `重新安裝 (${dllName})`);
    return L(`Patch with ${dllName}`, `以 ${dllName} 修補`);
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
      const result = await patchGame(selectedAppId, dllName, currentLaunchOptions, fsr4Variant);
      if (result.status !== "success") throw new Error(result.message || L("Patch failed.", "修補失敗。"));
      setAppLaunchOptions(Number(selectedAppId), result.launch_options || "");
      const msg = result.message || L(`Patched ${selectedGame.name}.`, `已修補 ${selectedGame.name}。`);
      setResultMessage(msg);
      toaster.toast({ title: "Decky Framegen", body: msg });
      await loadStatus(selectedAppId);
    } catch (err) {
      const msg = err instanceof Error ? err.message : L("Patch failed.", "修補失敗。");
      setResultMessage(L(`Error: ${msg}`, `錯誤：${msg}`));
      toaster.toast({ title: "Decky Framegen", body: msg });
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, dllName, fsr4Variant, loadStatus, selectedAppId, selectedGame]);

  const handleUnpatch = useCallback(async () => {
    if (!selectedGame || !selectedAppId || busyAction) return;
    setBusyAction("unpatch");
    setResultMessage("");
    try {
      const result = await unpatchGame(selectedAppId);
      if (result.status !== "success") throw new Error(result.message || L("Unpatch failed.", "還原修補失敗。"));
      setAppLaunchOptions(Number(selectedAppId), result.launch_options || "");
      const msg = result.message || L(`Unpatched ${selectedGame.name}.`, `已還原 ${selectedGame.name} 的修補。`);
      setResultMessage(msg);
      toaster.toast({ title: "Decky Framegen", body: msg });
      await loadStatus(selectedAppId);
    } catch (err) {
      const msg = err instanceof Error ? err.message : L("Unpatch failed.", "還原修補失敗。");
      setResultMessage(L(`Error: ${msg}`, `錯誤：${msg}`));
      toaster.toast({ title: "Decky Framegen", body: msg });
    } finally {
      setBusyAction(null);
    }
  }, [busyAction, loadStatus, selectedAppId, selectedGame]);

  // ── Status display ─────────────────────────────────────────────────────────

  const statusDisplay = useMemo(() => {
    if (!selectedGame) return { text: "—", color: undefined as string | undefined };
    if (statusLoading) return { text: L("Loading...", "載入中..."), color: undefined };
    if (!gameStatus || gameStatus.status === "error")
      return { text: gameStatus?.message || "—", color: undefined };
    if (!gameStatus.install_found) return { text: L("Install not found", "找不到安裝路徑"), color: "#ffd866" };
    if (!gameStatus.patched) return { text: L("Not patched", "未修補"), color: undefined };
    const dllLabel = gameStatus.dll_name || L("unknown", "未知");
    if (isPatchedWithDifferentDll)
      return { text: L(`Patched (${dllLabel}) — switch available`, `已修補 (${dllLabel}) — 可切換`), color: "#ffd866" };
    return { text: L(`Patched (${dllLabel})`, `已修補 (${dllLabel})`), color: "#3fb950" };
  }, [gameStatus, isPatchedWithDifferentDll, selectedGame, statusLoading]);

  const focusableFieldProps = { focusable: true, highlightOnFocus: true } as const;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <>
      <PanelSectionRow>
        <DropdownItem
          layout="below"
          label={L("Steam game", "Steam 遊戲")}
          menuLabel={L("Select a Steam game", "選擇 Steam 遊戲")}
          strDefaultLabel={gamesLoading ? L("Loading games...", "正在載入遊戲...") : L("Choose a game", "選擇遊戲")}
          disabled={gamesLoading || games.length === 0}
          selectedOption={selectedAppId}
          rgOptions={games.map((g) => ({
            data: g.appid,
            label: g.install_found === false ? `${g.name} ${L("(not installed)", "（未安裝）")}` : g.name,
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
            <Field {...focusableFieldProps} label={L("Patch status", "修補狀態")}>
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
            <Field {...focusableFieldProps} label={L("FSR4 runtime", "FSR4 執行環境")}>
              {gameStatus?.patched
                ? (gameStatus?.fsr4_variant_label || L("Unknown", "未知"))
                : L(`Will patch with ${selectedVariantLabel}`, `將使用 ${selectedVariantLabel} 修補`)}
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
                {busyAction === "unpatch" ? L("Unpatching...", "正在還原修補...") : L("Unpatch this game", "還原此遊戲修補")}
              </ButtonItem>
            </PanelSectionRow>
          )}

          <PanelSectionRow>
            <ButtonItem
              layout="below"
              disabled={!selectedAppId || busyAction !== null || statusLoading}
              onClick={() => void loadStatus(selectedAppId)}
            >
              {statusLoading ? L("Refreshing...", "正在重新整理...") : L("Refresh status", "重新整理狀態")}
            </ButtonItem>
          </PanelSectionRow>

          {resultMessage && (
            <PanelSectionRow>
              <Field {...focusableFieldProps} label={L("Result", "執行結果")}>
                {resultMessage}
              </Field>
            </PanelSectionRow>
          )}
        </>
      )}
    </>
  );
}

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ButtonItem,
  ConfirmModal,
  DropdownItem,
  Field,
  PanelSection,
  PanelSectionRow,
  SliderField,
  Router,
  showModal,
} from "@decky/ui";
import {
  cleanupManagedGame,
  getGameConfig,
  listInstalledGames,
  logError,
  saveGameConfig,
} from "../api";
import { safeAsyncOperation } from "../utils";
import type { ApiResponse, GameConfigResponse, GameInfo } from "../types/index";
import { STYLES } from "../utils/constants";

const DEFAULT_LAUNCH_COMMAND = "~/fgmod/fgmod %COMMAND%";
const POLL_INTERVAL_MS = 3000;

type RunningApp = {
  appid: string;
  display_name: string;
};

const PROXY_OPTIONS = ["winmm", "dxgi", "version", "dbghelp", "winhttp", "wininet", "d3d12"];
const UPSCALER_OPTIONS = ["auto", "fsr31", "xess", "dlss", "native"];
const TRI_STATE_OPTIONS = ["auto", "true", "false"];
const FG_INPUT_OPTIONS = ["auto", "fsrfg", "xefg", "dlssg"];
const FG_OUTPUT_OPTIONS = ["auto", "fsrfg", "xefg"];

const defaultQuickSettings = {
  Dx12Upscaler: "auto",
  "FrameGen.Enabled": "auto",
  FGInput: "auto",
  FGOutput: "auto",
  Fsr4ForceCapable: "false",
  Fsr4EnableWatermark: "false",
  UseHQFont: "false",
  "Menu.Scale": "1.000000",
};

interface InstalledGamesSectionProps {
  isAvailable: boolean;
}

const normalizeSettings = (settings?: Record<string, string>) => ({
  ...defaultQuickSettings,
  ...(settings || {}),
});

const formatResult = (result: ApiResponse | null, fallbackSuccess: string) => {
  if (!result) return "";
  if (result.status === "success") {
    return result.message || result.output || fallbackSuccess;
  }
  return `Error: ${result.message || result.output || "Operation failed"}`;
};

export function InstalledGamesSection({ isAvailable }: InstalledGamesSectionProps) {
  const [games, setGames] = useState<GameInfo[]>([]);
  const [selectedGame, setSelectedGame] = useState<GameInfo | null>(null);
  const [runningApps, setRunningApps] = useState<RunningApp[]>([]);
  const [mainRunningApp, setMainRunningApp] = useState<RunningApp | null>(null);
  const [loadingGames, setLoadingGames] = useState(false);
  const [enabling, setEnabling] = useState(false);
  const [disabling, setDisabling] = useState(false);
  const [configLoading, setConfigLoading] = useState(false);
  const [configResult, setConfigResult] = useState<string>("");
  const [config, setConfig] = useState<GameConfigResponse | null>(null);
  const [quickSettings, setQuickSettings] = useState<Record<string, string>>(defaultQuickSettings);
  const [selectedProxy, setSelectedProxy] = useState<string>("winmm");
  const [rawIni, setRawIni] = useState<string>("");
  const [savingQuick, setSavingQuick] = useState(false);
  const [savingQuickLive, setSavingQuickLive] = useState(false);
  const [savingRaw, setSavingRaw] = useState(false);
  const [savingRawLive, setSavingRawLive] = useState(false);

  const selectedAppId = selectedGame ? String(selectedGame.appid) : null;
  const selectedIsRunning = useMemo(
    () => Boolean(selectedAppId && runningApps.some((app) => String(app.appid) === selectedAppId)),
    [runningApps, selectedAppId]
  );

  const refreshRunningApps = useCallback(() => {
    try {
      const nextRunningApps = ((Router?.RunningApps || []) as RunningApp[])
        .filter((app) => app?.appid && app?.display_name)
        .map((app) => ({ appid: String(app.appid), display_name: app.display_name }));

      const nextMainRunningApp = Router?.MainRunningApp
        ? {
            appid: String(Router.MainRunningApp.appid),
            display_name: Router.MainRunningApp.display_name,
          }
        : nextRunningApps[0] || null;

      setRunningApps(nextRunningApps);
      setMainRunningApp(nextMainRunningApp);

      if (!selectedGame && nextMainRunningApp) {
        setSelectedGame({
          appid: nextMainRunningApp.appid,
          name: nextMainRunningApp.display_name,
        });
      }
    } catch (error) {
      console.error("InstalledGamesSection.refreshRunningApps", error);
    }
  }, [selectedGame]);

  const loadConfig = useCallback(
    async (appid: string) => {
      setConfigLoading(true);
      const response = await safeAsyncOperation(() => getGameConfig(appid), `InstalledGamesSection.loadConfig.${appid}`);
      if (!response) {
        setConfigLoading(false);
        return;
      }

      if (response.status === "success") {
        setConfig(response);
        setQuickSettings(normalizeSettings(response.settings));
        setSelectedProxy(response.proxy || "winmm");
        setRawIni(response.raw_ini || "");
        setConfigResult("");
      } else {
        setConfig(null);
        setConfigResult(`Error: ${response.message || response.output || "Failed to load game config"}`);
      }

      setConfigLoading(false);
    },
    []
  );

  useEffect(() => {
    if (!isAvailable) return;

    let cancelled = false;

    const fetchGames = async () => {
      setLoadingGames(true);
      const response = await safeAsyncOperation(async () => await listInstalledGames(), "InstalledGamesSection.fetchGames");
      if (cancelled || !response) {
        setLoadingGames(false);
        return;
      }

      if (response.status === "success") {
        const sortedGames = [...response.games]
          .map((game) => ({
            ...game,
            appid: parseInt(String(game.appid), 10),
          }))
          .sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
        setGames(sortedGames);
      } else {
        logError(`InstalledGamesSection.fetchGames: ${JSON.stringify(response)}`);
      }

      setLoadingGames(false);
    };

    fetchGames();
    refreshRunningApps();
    const interval = setInterval(refreshRunningApps, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [isAvailable, refreshRunningApps]);

  useEffect(() => {
    if (!isAvailable || !selectedAppId) return;
    void loadConfig(selectedAppId);
  }, [isAvailable, loadConfig, selectedAppId]);

  const handleEnable = async () => {
    if (!selectedGame) return;

    showModal(
      <ConfirmModal
        strTitle={`Enable prefix-managed OptiScaler for ${selectedGame.name}?`}
        strDescription={
          "This only changes the Steam launch option for the selected game. OptiScaler itself is staged into compatdata/pfx/system32 at launch time and does not write into the game install directory."
        }
        strOKButtonText="Enable"
        strCancelButtonText="Cancel"
        onOK={async () => {
          setEnabling(true);
          try {
            await SteamClient.Apps.SetAppLaunchOptions(selectedGame.appid, DEFAULT_LAUNCH_COMMAND);
            setConfigResult(`✓ Enabled prefix-managed OptiScaler for ${selectedGame.name}. Launch the game, enable DLSS if needed, then press Insert for the OptiScaler menu.`);
          } catch (error) {
            logError(`InstalledGamesSection.handleEnable: ${String(error)}`);
            setConfigResult(error instanceof Error ? `Error: ${error.message}` : "Error enabling prefix-managed OptiScaler");
          } finally {
            setEnabling(false);
          }
        }}
      />
    );
  };

  const handleDisable = async () => {
    if (!selectedGame) return;

    setDisabling(true);
    try {
      const cleanupResult = await cleanupManagedGame(String(selectedGame.appid));
      if (cleanupResult?.status !== "success") {
        setConfigResult(`Error: ${cleanupResult?.message || cleanupResult?.output || "Failed to clean managed compatdata prefix"}`);
        return;
      }

      await SteamClient.Apps.SetAppLaunchOptions(selectedGame.appid, "");
      setConfig(null);
      setQuickSettings(defaultQuickSettings);
      setSelectedProxy("winmm");
      setRawIni("");
      setConfigResult(`✓ Cleared launch options and cleaned the managed compatdata prefix for ${selectedGame.name}.`);
    } catch (error) {
      logError(`InstalledGamesSection.handleDisable: ${String(error)}`);
      setConfigResult(error instanceof Error ? `Error: ${error.message}` : "Error disabling prefix-managed OptiScaler");
    } finally {
      setDisabling(false);
    }
  };

  const saveQuickSettings = async (applyLive: boolean) => {
    if (!selectedAppId) return;

    const setBusy = applyLive ? setSavingQuickLive : setSavingQuick;
    setBusy(true);
    try {
      const response = await saveGameConfig(selectedAppId, quickSettings, selectedProxy, applyLive, null);
      setConfigResult(formatResult(response, applyLive ? "Applied config to the running game." : "Saved config."));
      await loadConfig(selectedAppId);
    } catch (error) {
      setConfigResult(error instanceof Error ? `Error: ${error.message}` : "Error saving config");
    } finally {
      setBusy(false);
    }
  };

  const saveRawEditor = async (applyLive: boolean) => {
    if (!selectedAppId) return;

    const setBusy = applyLive ? setSavingRawLive : setSavingRaw;
    setBusy(true);
    try {
      const response = await saveGameConfig(selectedAppId, {}, selectedProxy, applyLive, rawIni);
      setConfigResult(formatResult(response, applyLive ? "Applied raw INI to the running game." : "Saved raw INI."));
      await loadConfig(selectedAppId);
    } catch (error) {
      setConfigResult(error instanceof Error ? `Error: ${error.message}` : "Error saving raw INI");
    } finally {
      setBusy(false);
    }
  };

  if (!isAvailable) return null;

  return (
    <PanelSection title="Steam game integration + live config">
      <PanelSectionRow>
        <Field
          label="Running now"
          description={
            mainRunningApp
              ? `Main running game: ${mainRunningApp.display_name}`
              : "No running Steam game detected right now."
          }
        >
          <div style={{ ...STYLES.preWrap, fontSize: "12px" }}>
            {runningApps.length > 0
              ? runningApps.map((app) => app.display_name).join("\n")
              : "Idle"}
          </div>
        </Field>
      </PanelSectionRow>

      {mainRunningApp ? (
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={() =>
              setSelectedGame({
                appid: mainRunningApp.appid,
                name: mainRunningApp.display_name,
              })
            }
          >
            Use current running game
          </ButtonItem>
        </PanelSectionRow>
      ) : null}

      <PanelSectionRow>
        <DropdownItem
          rgOptions={games.map((game) => ({
            data: String(game.appid),
            label: game.name,
          }))}
          selectedOption={selectedAppId}
          onChange={(option) => {
            const game = games.find((entry) => String(entry.appid) === String(option.data));
            setSelectedGame(game || null);
            setConfigResult("");
          }}
          strDefaultLabel={loadingGames ? "Loading installed games..." : "Choose a game"}
          menuLabel="Installed Steam games"
          disabled={loadingGames || games.length === 0}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <div style={STYLES.instructionCard}>
          Enable writes the wrapper launch option automatically. Disable clears launch options and removes staged files from the selected game's compatdata prefix. The config editor below persists changes to the selected game and can also mirror them into the live prefix copy while the game is running.
        </div>
      </PanelSectionRow>

      {selectedGame ? (
        <>
          <PanelSectionRow>
            <Field
              label="Selected game"
              description={selectedIsRunning ? "Detected as currently running." : "Not currently running."}
            >
              {selectedGame.name}
            </Field>
          </PanelSectionRow>

          <PanelSectionRow>
            <ButtonItem layout="below" onClick={handleEnable} disabled={enabling || disabling}>
              {enabling ? "Enabling..." : "Enable for selected game"}
            </ButtonItem>
          </PanelSectionRow>

          <PanelSectionRow>
            <ButtonItem layout="below" onClick={handleDisable} disabled={enabling || disabling}>
              {disabling ? "Cleaning..." : "Disable and clean selected game"}
            </ButtonItem>
          </PanelSectionRow>

          <PanelSectionRow>
            <ButtonItem layout="below" onClick={() => loadConfig(String(selectedGame.appid))} disabled={configLoading}>
              {configLoading ? "Loading config..." : "Reload selected game config"}
            </ButtonItem>
          </PanelSectionRow>
        </>
      ) : null}

      {configResult ? (
        <PanelSectionRow>
          <div
            style={{
              ...STYLES.preWrap,
              ...(configResult.startsWith("Error") ? STYLES.statusNotInstalled : STYLES.statusInstalled),
            }}
          >
            {configResult.startsWith("Error") ? "❌" : "✅"} {configResult}
          </div>
        </PanelSectionRow>
      ) : null}

      {selectedGame && config ? (
        <>
          <PanelSectionRow>
            <Field
              label="Managed paths"
              description={config.live_available ? "Live prefix copy is present." : "Live prefix copy is not staged right now."}
            >
              <div style={{ ...STYLES.preWrap, fontSize: "11px", wordBreak: "break-word" }}>
                {config.paths?.managed_ini ? `Managed INI: ${config.paths.managed_ini}\n` : ""}
                {config.paths?.live_ini ? `Live INI: ${config.paths.live_ini}` : ""}
              </div>
            </Field>
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              rgOptions={PROXY_OPTIONS.map((proxy) => ({ data: proxy, label: proxy }))}
              selectedOption={selectedProxy}
              onChange={(option) => setSelectedProxy(String(option.data))}
              menuLabel="Proxy DLL"
              strDefaultLabel="Proxy DLL"
              description="Persisted per game and used by the wrapper on next launch."
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              rgOptions={UPSCALER_OPTIONS.map((value) => ({ data: value, label: value }))}
              selectedOption={quickSettings.Dx12Upscaler}
              onChange={(option) => setQuickSettings((prev) => ({ ...prev, Dx12Upscaler: String(option.data) }))}
              menuLabel="DX12 upscaler"
              strDefaultLabel="DX12 upscaler"
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              rgOptions={TRI_STATE_OPTIONS.map((value) => ({ data: value, label: value }))}
              selectedOption={quickSettings["FrameGen.Enabled"]}
              onChange={(option) => setQuickSettings((prev) => ({ ...prev, "FrameGen.Enabled": String(option.data) }))}
              menuLabel="Frame generation enabled"
              strDefaultLabel="Frame generation enabled"
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              rgOptions={FG_INPUT_OPTIONS.map((value) => ({ data: value, label: value }))}
              selectedOption={quickSettings.FGInput}
              onChange={(option) => setQuickSettings((prev) => ({ ...prev, FGInput: String(option.data) }))}
              menuLabel="FG input"
              strDefaultLabel="FG input"
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              rgOptions={FG_OUTPUT_OPTIONS.map((value) => ({ data: value, label: value }))}
              selectedOption={quickSettings.FGOutput}
              onChange={(option) => setQuickSettings((prev) => ({ ...prev, FGOutput: String(option.data) }))}
              menuLabel="FG output"
              strDefaultLabel="FG output"
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              rgOptions={TRI_STATE_OPTIONS.map((value) => ({ data: value, label: value }))}
              selectedOption={quickSettings.Fsr4ForceCapable}
              onChange={(option) => setQuickSettings((prev) => ({ ...prev, Fsr4ForceCapable: String(option.data) }))}
              menuLabel="FSR4 force capable"
              strDefaultLabel="FSR4 force capable"
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              rgOptions={TRI_STATE_OPTIONS.map((value) => ({ data: value, label: value }))}
              selectedOption={quickSettings.Fsr4EnableWatermark}
              onChange={(option) => setQuickSettings((prev) => ({ ...prev, Fsr4EnableWatermark: String(option.data) }))}
              menuLabel="FSR4 watermark"
              strDefaultLabel="FSR4 watermark"
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              rgOptions={TRI_STATE_OPTIONS.map((value) => ({ data: value, label: value }))}
              selectedOption={quickSettings.UseHQFont}
              onChange={(option) => setQuickSettings((prev) => ({ ...prev, UseHQFont: String(option.data) }))}
              menuLabel="Use HQ font"
              strDefaultLabel="Use HQ font"
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <SliderField
              label="Menu scale"
              value={Number.parseFloat(quickSettings["Menu.Scale"] || "1") || 1}
              min={0.5}
              max={2.0}
              step={0.05}
              showValue
              editableValue
              onChange={(value) =>
                setQuickSettings((prev) => ({
                  ...prev,
                  "Menu.Scale": value.toFixed(6),
                }))
              }
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <ButtonItem layout="below" onClick={() => saveQuickSettings(false)} disabled={savingQuick || savingQuickLive}>
              {savingQuick ? "Saving..." : "Apply + persist quick settings"}
            </ButtonItem>
          </PanelSectionRow>

          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={() => saveQuickSettings(true)}
              disabled={!selectedIsRunning || savingQuick || savingQuickLive}
            >
              {savingQuickLive ? "Applying live..." : "Apply quick settings to running game now"}
            </ButtonItem>
          </PanelSectionRow>

          <PanelSectionRow>
            <Field
              label="Advanced raw INI editor"
              description="Edits the selected game's OptiScaler.ini directly. Use this for settings not exposed above."
            >
              <textarea
                value={rawIni}
                onChange={(event) => setRawIni(event.target.value)}
                style={{
                  width: "100%",
                  minHeight: "280px",
                  resize: "vertical",
                  boxSizing: "border-box",
                  borderRadius: "8px",
                  border: "1px solid var(--decky-border-color)",
                  background: "rgba(255,255,255,0.05)",
                  color: "inherit",
                  padding: "10px",
                  fontFamily: "monospace",
                  fontSize: "11px",
                }}
              />
            </Field>
          </PanelSectionRow>

          <PanelSectionRow>
            <ButtonItem layout="below" onClick={() => saveRawEditor(false)} disabled={savingRaw || savingRawLive}>
              {savingRaw ? "Saving raw INI..." : "Save raw INI"}
            </ButtonItem>
          </PanelSectionRow>

          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={() => saveRawEditor(true)}
              disabled={!selectedIsRunning || savingRaw || savingRawLive}
            >
              {savingRawLive ? "Applying raw INI live..." : "Save raw INI + apply live"}
            </ButtonItem>
          </PanelSectionRow>
        </>
      ) : null}
    </PanelSection>
  );
}

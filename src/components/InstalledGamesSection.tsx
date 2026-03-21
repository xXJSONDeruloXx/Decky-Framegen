import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ButtonItem,
  ConfirmModal,
  DropdownItem,
  Field,
  PanelSection,
  PanelSectionRow,
  SliderField,
  TextField,
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
import type {
  ApiResponse,
  GameConfigResponse,
  GameConfigSettingSchema,
  GameInfo,
} from "../types/index";
import { STYLES } from "../utils/constants";

const DEFAULT_LAUNCH_COMMAND = "~/fgmod/fgmod %COMMAND%";
const POLL_INTERVAL_MS = 3000;
const AUTOSAVE_DELAY_MS = 500;

type RunningApp = {
  appid: string;
  display_name: string;
};

interface InstalledGamesSectionProps {
  isAvailable: boolean;
}

const formatResult = (result: ApiResponse | null, fallbackSuccess: string) => {
  if (!result) return "";
  if (result.status === "success") {
    return result.message || result.output || fallbackSuccess;
  }
  return `Error: ${result.message || result.output || "Operation failed"}`;
};

const buildSignature = (proxy: string, settings: Record<string, string>) =>
  JSON.stringify({ proxy, settings });

const valueForSetting = (settings: Record<string, string>, setting: GameConfigSettingSchema) =>
  settings[setting.id] ?? setting.default ?? "auto";

const defaultNumericValue = (setting: GameConfigSettingSchema) => {
  const parsedDefault = Number.parseFloat(setting.default ?? "");
  if (Number.isFinite(parsedDefault)) return parsedDefault;
  if (typeof setting.rangeMin === "number") return setting.rangeMin;
  return 0;
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
  const [settingValues, setSettingValues] = useState<Record<string, string>>({});
  const [selectedProxy, setSelectedProxy] = useState<string>("winmm");
  const [selectedSectionId, setSelectedSectionId] = useState<string>("");
  const [autoSaving, setAutoSaving] = useState(false);

  const skipAutosaveRef = useRef(true);
  const lastLoadedSignatureRef = useRef<string>("");

  const selectedAppId = selectedGame ? String(selectedGame.appid) : null;
  const selectedIsRunning = useMemo(
    () => Boolean(selectedAppId && runningApps.some((app) => String(app.appid) === selectedAppId)),
    [runningApps, selectedAppId]
  );

  const sectionOptions = useMemo(
    () =>
      (config?.schema || []).map((section) => ({
        data: section.id,
        label: `${section.label} (${section.settings.length})`,
      })),
    [config?.schema]
  );

  const activeSection = useMemo(
    () => (config?.schema || []).find((section) => section.id === selectedSectionId) || config?.schema?.[0] || null,
    [config?.schema, selectedSectionId]
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
        skipAutosaveRef.current = true;
        setConfig(response);
        setSettingValues(response.settings || {});
        setSelectedProxy(response.proxy || "winmm");
        setSelectedSectionId((current) =>
          current && response.schema?.some((section) => section.id === current)
            ? current
            : response.schema?.[0]?.id || ""
        );
        setConfigResult("");
        lastLoadedSignatureRef.current = buildSignature(response.proxy || "winmm", response.settings || {});
      } else {
        setConfig(null);
        setSettingValues({});
        setSelectedSectionId("");
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

  useEffect(() => {
    if (!selectedAppId || !config?.schema?.length) return;

    const currentSignature = buildSignature(selectedProxy, settingValues);
    if (skipAutosaveRef.current) {
      skipAutosaveRef.current = false;
      lastLoadedSignatureRef.current = currentSignature;
      return;
    }

    if (currentSignature === lastLoadedSignatureRef.current) {
      return;
    }

    const timer = setTimeout(async () => {
      setAutoSaving(true);
      try {
        const response = await saveGameConfig(selectedAppId, settingValues, selectedProxy, selectedIsRunning, null);
        if (response.status === "success") {
          const updated = response as GameConfigResponse;
          skipAutosaveRef.current = true;
          setConfig(updated);
          setSettingValues(updated.settings || settingValues);
          setSelectedProxy(updated.proxy || selectedProxy);
          setSelectedSectionId((current) =>
            current && updated.schema?.some((section) => section.id === current)
              ? current
              : updated.schema?.[0]?.id || ""
          );
          lastLoadedSignatureRef.current = buildSignature(updated.proxy || selectedProxy, updated.settings || settingValues);
          setConfigResult(
            response.message ||
              (selectedIsRunning
                ? "Applied config immediately to the running game."
                : "Saved config for the selected game.")
          );
        } else {
          setConfigResult(formatResult(response, "Failed to save config."));
        }
      } catch (error) {
        setConfigResult(error instanceof Error ? `Error: ${error.message}` : "Error saving config");
      } finally {
        setAutoSaving(false);
      }
    }, AUTOSAVE_DELAY_MS);

    return () => clearTimeout(timer);
  }, [config?.schema, selectedAppId, selectedIsRunning, selectedProxy, settingValues]);

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
      setSettingValues({});
      setSelectedProxy("winmm");
      setSelectedSectionId("");
      setConfigResult(`✓ Cleared launch options and cleaned the managed compatdata prefix for ${selectedGame.name}.`);
    } catch (error) {
      logError(`InstalledGamesSection.handleDisable: ${String(error)}`);
      setConfigResult(error instanceof Error ? `Error: ${error.message}` : "Error disabling prefix-managed OptiScaler");
    } finally {
      setDisabling(false);
    }
  };

  const updateSettingValue = (settingId: string, value: string) => {
    setSettingValues((prev) => ({ ...prev, [settingId]: value }));
  };

  const renderSettingControl = (setting: GameConfigSettingSchema) => {
    const currentValue = valueForSetting(settingValues, setting);

    if (setting.control === "dropdown") {
      const options = [...setting.options];
      if (!options.some((option) => option.value === currentValue)) {
        options.push({ value: currentValue, label: currentValue });
      }

      return (
        <PanelSectionRow key={setting.id}>
          <DropdownItem
            label={setting.label}
            description={setting.description}
            rgOptions={options.map((option) => ({ data: option.value, label: option.label }))}
            selectedOption={currentValue}
            onChange={(option) => updateSettingValue(setting.id, String(option.data))}
            menuLabel={setting.label}
            strDefaultLabel={setting.label}
          />
        </PanelSectionRow>
      );
    }

    if (setting.control === "range") {
      const isAuto = currentValue === "auto";
      const numericValue = Number.parseFloat(currentValue);
      const effectiveValue = Number.isFinite(numericValue) ? numericValue : defaultNumericValue(setting);

      return (
        <div key={setting.id}>
          <PanelSectionRow>
            <DropdownItem
              label={setting.label}
              description={setting.description}
              rgOptions={[
                { data: "auto", label: "auto" },
                { data: "custom", label: "custom" },
              ]}
              selectedOption={isAuto ? "auto" : "custom"}
              onChange={(option) => {
                if (String(option.data) === "auto") {
                  updateSettingValue(setting.id, "auto");
                } else if (currentValue === "auto") {
                  const baseValue = defaultNumericValue(setting);
                  updateSettingValue(
                    setting.id,
                    setting.numericType === "float" ? baseValue.toFixed(2) : String(Math.round(baseValue))
                  );
                }
              }}
              menuLabel={`${setting.label} mode`}
              strDefaultLabel={`${setting.label} mode`}
            />
          </PanelSectionRow>
          {!isAuto ? (
            <PanelSectionRow>
              <SliderField
                label={`${setting.label} value`}
                value={effectiveValue}
                min={setting.rangeMin ?? 0}
                max={setting.rangeMax ?? 1}
                step={setting.step ?? 1}
                showValue
                editableValue
                onChange={(value) =>
                  updateSettingValue(
                    setting.id,
                    setting.numericType === "float" ? value.toFixed(2) : String(Math.round(value))
                  )
                }
              />
            </PanelSectionRow>
          ) : null}
        </div>
      );
    }

    return (
      <PanelSectionRow key={setting.id}>
        <TextField
          label={setting.label}
          description={setting.description}
          value={currentValue}
          onChange={(event) => updateSettingValue(setting.id, event.currentTarget.value)}
        />
      </PanelSectionRow>
    );
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
            {runningApps.length > 0 ? runningApps.map((app) => app.display_name).join("\n") : "Idle"}
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
          label="Target game"
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
          Enable writes the wrapper launch option automatically. Disable clears launch options and removes staged files from the selected game's compatdata prefix. All config controls below now autosave immediately, and if the selected game is running they also update the live prefix copy automatically.
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

      {configResult || autoSaving ? (
        <PanelSectionRow>
          <div
            style={{
              ...STYLES.preWrap,
              ...((configResult.startsWith("Error") ? STYLES.statusNotInstalled : STYLES.statusInstalled) as object),
            }}
          >
            {autoSaving ? "💾 Autosaving configuration..." : null}
            {autoSaving && configResult ? "\n" : null}
            {configResult ? `${configResult.startsWith("Error") ? "❌" : "✅"} ${configResult}` : null}
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
              label="Proxy DLL"
              description="Persisted per game and used by the wrapper on next launch. Changes autosave immediately."
              rgOptions={["winmm", "dxgi", "version", "dbghelp", "winhttp", "wininet", "d3d12"].map((proxy) => ({
                data: proxy,
                label: proxy,
              }))}
              selectedOption={selectedProxy}
              onChange={(option) => setSelectedProxy(String(option.data))}
              menuLabel="Proxy DLL"
              strDefaultLabel="Proxy DLL"
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              label="Config section"
              description="Browse and edit every setting parsed from the bundled OptiScaler.ini template."
              rgOptions={sectionOptions}
              selectedOption={selectedSectionId}
              onChange={(option) => setSelectedSectionId(String(option.data))}
              menuLabel="Config section"
              strDefaultLabel="Config section"
              disabled={sectionOptions.length === 0}
            />
          </PanelSectionRow>

          {activeSection ? (
            <>
              <PanelSectionRow>
                <Field
                  label={activeSection.label}
                  description={`Showing ${activeSection.settings.length} setting${activeSection.settings.length === 1 ? "" : "s"} in this section.`}
                >
                  {selectedIsRunning
                    ? "Changes in this section will be applied to the managed config and the live prefix copy."
                    : "Changes in this section will be saved for the next launch unless the game is already running."}
                </Field>
              </PanelSectionRow>
              {activeSection.settings.map(renderSettingControl)}
            </>
          ) : null}
        </>
      ) : null}
    </PanelSection>
  );
}

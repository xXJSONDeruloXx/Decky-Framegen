import { useCallback, useEffect, useMemo, useState } from "react";
import { ButtonItem, Field, PanelSectionRow, ToggleField } from "@decky/ui";
import { FileSelectionType, openFilePicker } from "@decky/api";
import { getPathDefaults, runManualPatch, runManualUnpatch } from "../api";
import type { ApiResponse } from "../types/index";
import { SmartClipboardButton } from "./SmartClipboardButton";
import { L } from "../utils/i18n";

interface PathDefaults {
  home: string;
  steamCommon: string;
}

const DEFAULT_HOME = "/home";
const DEFAULT_STEAM_COMMON = "/home/deck/.local/share/Steam/steamapps/common";

const INITIAL_DEFAULTS: PathDefaults = {
  home: DEFAULT_HOME,
  steamCommon: DEFAULT_STEAM_COMMON,
};

const normalizePath = (value: string) => value.replace(/\\/g, "/");

const stripTrailingSlash = (value: string) =>
  value.length > 1 && value.endsWith("/") ? value.slice(0, -1) : value;

const ensureDirectory = (value: string) => {
  const normalized = normalizePath(value);
  const lastSegment = normalized.substring(normalized.lastIndexOf("/") + 1);
  if (!lastSegment || !lastSegment.includes(".")) {
    return stripTrailingSlash(normalized);
  }
  const parent = normalized.slice(0, normalized.lastIndexOf("/"));
  return parent || "/";
};

interface ManualPatchControlsProps {
  isAvailable: boolean;
  onManualModeChange?: (enabled: boolean) => void;
  dllName: string;
  fsr4Variant: string;
}

interface PickerState {
  selectedPath: string | null;
  lastError: string | null;
}

const INITIAL_PICKER_STATE: PickerState = {
  selectedPath: null,
  lastError: null,
};

const formatResultMessage = (result: ApiResponse | null) => {
  if (!result) return null;
  if (result.status === "success") {
    return result.message || result.output || L("Operation completed successfully.", "操作已順利完成。");
  }
  return result.message || result.output || L("Operation failed.", "操作失敗。");
};

export const ManualPatchControls = ({ isAvailable, onManualModeChange, dllName, fsr4Variant }: ManualPatchControlsProps) => {
  const [isEnabled, setEnabled] = useState(false);
  const [defaults, setDefaults] = useState<PathDefaults>(INITIAL_DEFAULTS);
  const [pickerState, setPickerState] = useState<PickerState>(INITIAL_PICKER_STATE);
  const [isPatching, setIsPatching] = useState(false);
  const [isUnpatching, setIsUnpatching] = useState(false);
  const [operationResult, setOperationResult] = useState<ApiResponse | null>(null);
  const [lastOperation, setLastOperation] = useState<"patch" | "unpatch" | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const response = await getPathDefaults();
        if (!response || cancelled) return;

        const home = response.home ? normalizePath(response.home) : DEFAULT_HOME;
        const steamCommon = response.steam_common
          ? normalizePath(response.steam_common)
          : normalizePath(`${stripTrailingSlash(home)}/.local/share/Steam/steamapps/common`);

        setDefaults({
          home,
          steamCommon: steamCommon || DEFAULT_STEAM_COMMON,
        });
      } catch (err) {
        console.error("ManualPatchControls -> getPathDefaults", err);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!isAvailable) {
      setEnabled(false);
      setPickerState(INITIAL_PICKER_STATE);
      setOperationResult(null);
      setLastOperation(null);
      onManualModeChange?.(false);
    }
  }, [isAvailable, onManualModeChange]);

  const canInteract = isAvailable && isEnabled;
  const selectedPath = pickerState.selectedPath;
  const statusMessage = useMemo(() => formatResultMessage(operationResult), [operationResult]);
  const wasSuccessful = operationResult?.status === "success";
  const statusLabel = useMemo(() => {
    if (!operationResult || !lastOperation) return null;
    if (operationResult.status === "success") {
      return lastOperation === "patch" ? L("Game patched", "遊戲已修補") : L("Game unpatched", "遊戲已還原");
    }
    return lastOperation === "patch" ? L("Patch failed", "修補失敗") : L("Unpatch failed", "還原失敗");
  }, [lastOperation, operationResult]);

  const openDirectoryPicker = useCallback(async () => {
    const candidates = [
      selectedPath,
      defaults.steamCommon,
      defaults.home,
    ];

    let lastError: string | null = null;

    for (const candidate of candidates) {
      if (!candidate) continue;

      const startPath = ensureDirectory(candidate);

      try {
        const result = await openFilePicker(
          FileSelectionType.FOLDER,
          startPath,
          true,
          true,
          undefined,
          undefined,
          true
        );

        if (result?.path) {
          setPickerState({ selectedPath: normalizePath(result.path), lastError: null });
          setOperationResult(null);
          return;
        }
      } catch (err) {
        console.error("ManualPatchControls -> openDirectoryPicker", err);
        lastError = err instanceof Error ? err.message : String(err);
      }
    }

    setPickerState((prev) => ({ ...prev, lastError }));
  }, [defaults.home, defaults.steamCommon, selectedPath]);

  const runOperation = useCallback(
    async (action: "patch" | "unpatch") => {
      if (!selectedPath) return;

      const setBusy = action === "patch" ? setIsPatching : setIsUnpatching;
  setLastOperation(action);
      setBusy(true);
      setOperationResult(null);

      try {
        const response =
          action === "patch"
            ? await runManualPatch(selectedPath, dllName, fsr4Variant)
            : await runManualUnpatch(selectedPath);
        setOperationResult(response ?? { status: "error", message: L("No response from backend.", "後端未回應。") });
      } catch (err) {
        setOperationResult({
          status: "error",
          message: err instanceof Error ? err.message : String(err),
        });
      } finally {
        setBusy(false);
      }
    },
    [selectedPath, dllName, fsr4Variant]
  );

  const handleToggle = (value: boolean) => {
    if (!isAvailable) {
      setEnabled(false);
      return;
    }

    setEnabled(value);
    onManualModeChange?.(value);
    if (!value) {
      setPickerState(INITIAL_PICKER_STATE);
      setOperationResult(null);
      setLastOperation(null);
    }
  };

  const busy = isPatching || isUnpatching;

  return (
    <>
      <PanelSectionRow>
        <ToggleField
          label={L("Advanced Mode", "進階模式")}
          description={
            isAvailable
              ? L("Manually apply OptiScaler to a specific game directory.", "手動對特定遊戲資料夾套用 OptiScaler。")
              : L("Install OptiScaler first to enable manual patching.", "請先安裝 OptiScaler 才能啟用手動修補。")
          }
          checked={isEnabled && isAvailable}
          disabled={!isAvailable}
          onChange={handleToggle}
        />
      </PanelSectionRow>

      {canInteract && (
        <>
          <SmartClipboardButton
            command={
              dllName === "OptiScaler.asi"
                ? "SteamDeck=0 %command%"
                : `WINEDLLOVERRIDES="${dllName.replace(".dll", "")}=n,b" SteamDeck=0 %command%`
            }
            buttonText={L("Manual launch cmd", "複製手動啟動指令")}
          />
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={openDirectoryPicker}
              description={L("Choose the game's installation directory (where the EXE lives).", "選擇遊戲的安裝資料夾（EXE 執行檔所在位置）。")}
            >
              {L("Select directory", "選擇資料夾")}
            </ButtonItem>
          </PanelSectionRow>

          {pickerState.lastError && (
            <PanelSectionRow>
              <Field
                label={L("Picker error", "資料夾選擇器錯誤")}
                description={pickerState.lastError}
              />
            </PanelSectionRow>
          )}

          {selectedPath && (
            <>
              <PanelSectionRow>
                <Field
                  label={L("Target directory", "目標資料夾")}
                  description={L("OptiScaler files will be copied here.", "OptiScaler 檔案將會複製至此處。")}
                >
                  <div
                    style={{
                      fontFamily: "monospace",
                      backgroundColor: "rgba(255, 255, 255, 0.05)",
                      border: "1px solid rgba(255, 255, 255, 0.1)",
                      borderRadius: "4px",
                      padding: "6px 8px",
                      width: "100%",
                      boxSizing: "border-box",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                    }}
                  >
                    {selectedPath}
                  </div>
                </Field>
              </PanelSectionRow>

              <PanelSectionRow>
                <ButtonItem
                  layout="below"
                  disabled={busy}
                  onClick={() => runOperation("patch")}
                >
                  {isPatching ? L("Patching...", "正在修補...") : L("Patch directory", "修補此資料夾")}
                </ButtonItem>
              </PanelSectionRow>

              <PanelSectionRow>
                <ButtonItem
                  layout="below"
                  disabled={busy}
                  onClick={() => runOperation("unpatch")}
                >
                  {isUnpatching ? L("Reverting...", "正在還原...") : L("Unpatch directory", "還原此資料夾")}
                </ButtonItem>
              </PanelSectionRow>
            </>
          )}

          {operationResult && (
            <PanelSectionRow>
              <Field
                label={statusLabel ?? (wasSuccessful ? L("Last action succeeded", "上次操作成功") : L("Last action failed", "上次操作失敗"))}
              >
                {!wasSuccessful && statusMessage ? statusMessage : null}
              </Field>
            </PanelSectionRow>
          )}
        </>
      )}
    </>
  );
};
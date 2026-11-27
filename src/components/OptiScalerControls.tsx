import { useState, useEffect } from "react";
import { DropdownItem, Field, PanelSection, PanelSectionRow, ToggleField } from "@decky/ui";
import { runInstallFGMod, runUninstallFGMod, setDefaultFsr4Variant } from "../api";
import { OperationResult } from "./ResultDisplay";
import { createAutoCleanupTimer } from "../utils";
import { TIMEOUTS, PROXY_DLL_OPTIONS, DEFAULT_PROXY_DLL, FSR4_VARIANT_OPTIONS, DEFAULT_FSR4_VARIANT } from "../utils/constants";
import { L } from "../utils/i18n";
import { InstallationStatus } from "./InstallationStatus";
import { OptiScalerHeader } from "./OptiScalerHeader";
import { ClipboardCommands } from "./ClipboardCommands";
import { InstructionCard } from "./InstructionCard";
import { OptiScalerWiki } from "./OptiScalerWiki";
import { UninstallButton } from "./UninstallButton";
import { ManualPatchControls } from "./CustomPathOverride";
import { SteamGamePatcher } from "./SteamGamePatcher";

interface FgmodInfo {
  exists: boolean;
  version?: string | null;
  selected_fsr4_variant?: string | null;
  selected_fsr4_variant_label?: string | null;
  install_manifest_present?: boolean;
}

interface OptiScalerControlsProps {
  pathExists: boolean | null;
  setPathExists: (exists: boolean | null) => void;
  fgmodInfo?: FgmodInfo | null;
}

export function OptiScalerControls({ pathExists, setPathExists, fgmodInfo }: OptiScalerControlsProps) {
  const [installing, setInstalling] = useState(false);
  const [uninstalling, setUninstalling] = useState(false);
  const [installResult, setInstallResult] = useState<OperationResult | null>(null);
  const [uninstallResult, setUninstallResult] = useState<OperationResult | null>(null);
  const [advancedModeEnabled, setAdvancedModeEnabled] = useState(false);
  const [manualClipboardModeEnabled, setManualClipboardModeEnabled] = useState(false);
  const [dllName, setDllName] = useState<string>(DEFAULT_PROXY_DLL);
  const [fsr4Variant, setFsr4Variant] = useState<string>(DEFAULT_FSR4_VARIANT);
  const [fsr4VariantTouched, setFsr4VariantTouched] = useState(false);
  const [switchingVariant, setSwitchingVariant] = useState(false);
  useEffect(() => {
    if (installResult) {
      return createAutoCleanupTimer(() => setInstallResult(null), TIMEOUTS.resultDisplay);
    }
    return () => {}; // Ensure a cleanup function is always returned
  }, [installResult]);

  useEffect(() => {
    if (uninstallResult) {
      return createAutoCleanupTimer(() => setUninstallResult(null), TIMEOUTS.resultDisplay);
    }
    return () => {}; // Ensure a cleanup function is always returned
  }, [uninstallResult]);

  useEffect(() => {
    const installedVariant = fgmodInfo?.selected_fsr4_variant;
    if (!fsr4VariantTouched && installedVariant && FSR4_VARIANT_OPTIONS.some((option) => option.value === installedVariant)) {
      setFsr4Variant(installedVariant);
    }
  }, [fgmodInfo?.selected_fsr4_variant, fsr4VariantTouched]);

  const handleInstallClick = async () => {
    try {
      setInstalling(true);
      const result = await runInstallFGMod(fsr4Variant);
      setInstallResult(result);
      if (result.status === "success") {
        setPathExists(true);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setInstalling(false);
    }
  };

  const handleUninstallClick = async () => {
    try {
      setUninstalling(true);
      const result = await runUninstallFGMod();
      setUninstallResult(result);
      if (result.status === "success") {
        setPathExists(false);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setUninstalling(false);
    }
  };

  const handleFsr4VariantChange = async (nextVariant: string) => {
    const previousVariant = fsr4Variant;
    setFsr4Variant(nextVariant);
    setFsr4VariantTouched(true);

    if (pathExists !== true) return;

    try {
      setSwitchingVariant(true);
      const result = await setDefaultFsr4Variant(nextVariant);
      if (result.status !== "success") {
        throw new Error(result.message || result.output || L("Failed to switch default FSR4 runtime.", "無法切換預設 FSR4 執行環境。"));
      }
      setFsr4Variant(result.selected_default_variant || nextVariant);
      setFsr4VariantTouched(false);
    } catch (error) {
      console.error(error);
      setFsr4Variant(previousVariant);
    } finally {
      setSwitchingVariant(false);
    }
  };

  const installedVariantLabel = fgmodInfo?.selected_fsr4_variant_label || FSR4_VARIANT_OPTIONS.find((option) => option.value === fsr4Variant)?.label;

  return (
    <PanelSection>
      <InstallationStatus 
        pathExists={pathExists}
        installing={installing}
        onInstallClick={handleInstallClick}
      />
      
      <OptiScalerHeader pathExists={pathExists} />

      <PanelSectionRow>
        <DropdownItem
          layout="below"
          label={L("Default FSR4 runtime", "預設 FSR4 執行環境")}
          description={FSR4_VARIANT_OPTIONS.find((option) => option.value === fsr4Variant)?.hint}
          menuLabel={L("Default FSR4 runtime", "預設 FSR4 執行環境")}
          selectedOption={fsr4Variant}
          rgOptions={FSR4_VARIANT_OPTIONS.map((option) => ({ data: option.value, label: option.label }))}
          disabled={installing || uninstalling || switchingVariant}
          onChange={(option) => {
            void handleFsr4VariantChange(String(option.data));
          }}
        />
      </PanelSectionRow>

      {pathExists === true && fgmodInfo?.version && installedVariantLabel && (
        <PanelSectionRow>
          <Field label={L("Installed bundle", "已安裝套件")} description={`OptiScaler ${fgmodInfo.version}`}>
            {installedVariantLabel}
          </Field>
        </PanelSectionRow>
      )}

      {pathExists === true && (
        <PanelSectionRow>
          <DropdownItem
            layout="below"
            label={L("Proxy DLL name", "代理 DLL 名稱")}
            description={PROXY_DLL_OPTIONS.find((o) => o.value === dllName)?.hint}
            menuLabel={L("Proxy DLL name", "代理 DLL 名稱")}
            selectedOption={dllName}
            rgOptions={PROXY_DLL_OPTIONS.map((o) => ({ data: o.value, label: o.label }))}
            onChange={(option) => setDllName(String(option.data))}
          />
        </PanelSectionRow>
      )}

      {pathExists === true && (
        <SteamGamePatcher dllName={dllName} fsr4Variant={fsr4Variant} />
      )}

      <ClipboardCommands pathExists={pathExists} dllName={dllName} />

      {pathExists === true && (
        <PanelSectionRow>
          <ToggleField
            label={L("Manual Mode", "手動模式")}
            description={L(
              "Show wrapper command clipboard buttons for patching and unpatching through ~/fgmod scripts.",
              "顯示透過 ~/fgmod 腳本進行修補與還原的包裝指令複製按鈕。",
            )}
            checked={manualClipboardModeEnabled}
            onChange={setManualClipboardModeEnabled}
          />
        </PanelSectionRow>
      )}

      {pathExists === true && manualClipboardModeEnabled ? (
        <ClipboardCommands
          pathExists={pathExists}
          dllName={dllName}
          manualModeEnabled
          showLaunchOptions={false}
        />
      ) : null}

      <ManualPatchControls
        isAvailable={pathExists === true}
        onManualModeChange={setAdvancedModeEnabled}
        dllName={dllName}
        fsr4Variant={fsr4Variant}
      />

      {!advancedModeEnabled && (
        <InstructionCard pathExists={pathExists} />
      )}
      <OptiScalerWiki pathExists={pathExists} />
      
      <UninstallButton 
        pathExists={pathExists}
        uninstalling={uninstalling}
        onUninstallClick={handleUninstallClick}
      />
    </PanelSection>
  );
}

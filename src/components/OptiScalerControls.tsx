import { useState, useEffect } from "react";
import { DropdownItem, Field, PanelSection, PanelSectionRow, ToggleField } from "@decky/ui";
import { runInstallFGMod, runUninstallFGMod, setDefaultFsr4Variant, setFramegenBackend } from "../api";
import { ResultDisplay, type OperationResult } from "./ResultDisplay";
import { createAutoCleanupTimer } from "../utils";
import {
  TIMEOUTS,
  PROXY_DLL_OPTIONS,
  DEFAULT_PROXY_DLL,
  FSR4_VARIANT_OPTIONS,
  DEFAULT_FSR4_VARIANT,
  FRAMEGEN_BACKEND_OPTIONS,
  DEFAULT_FRAMEGEN_BACKEND,
} from "../utils/constants";
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
  framegen_backend?: string | null;
  framegen_backend_label?: string | null;
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
  const [framegenBackend, setFramegenBackendValue] = useState<string>(DEFAULT_FRAMEGEN_BACKEND);
  const [framegenBackendTouched, setFramegenBackendTouched] = useState(false);
  const [switchingVariant, setSwitchingVariant] = useState(false);
  const [switchingBackend, setSwitchingBackend] = useState(false);
  useEffect(() => {
    if (installResult) {
      return createAutoCleanupTimer(() => setInstallResult(null), TIMEOUTS.resultDisplay);
    }
    return undefined;
  }, [installResult]);

  useEffect(() => {
    if (uninstallResult) {
      return createAutoCleanupTimer(() => setUninstallResult(null), TIMEOUTS.resultDisplay);
    }
    return undefined;
  }, [uninstallResult]);

  useEffect(() => {
    const installedVariant = fgmodInfo?.selected_fsr4_variant;
    if (!fsr4VariantTouched && installedVariant && FSR4_VARIANT_OPTIONS.some((option) => option.value === installedVariant)) {
      setFsr4Variant(installedVariant);
    }
  }, [fgmodInfo?.selected_fsr4_variant, fsr4VariantTouched]);

  useEffect(() => {
    const installedBackend = fgmodInfo?.framegen_backend;
    if (!framegenBackendTouched && installedBackend && FRAMEGEN_BACKEND_OPTIONS.some((option) => option.value === installedBackend)) {
      setFramegenBackendValue(installedBackend);
    }
  }, [fgmodInfo?.framegen_backend, framegenBackendTouched]);

  const handleInstallClick = async () => {
    try {
      setInstalling(true);
      const result = await runInstallFGMod(fsr4Variant, framegenBackend);
      setInstallResult(result);
      if (result.status === "success") {
        setPathExists(true);
        setFsr4VariantTouched(false);
        setFramegenBackendTouched(false);
      }
    } catch (e) {
      console.error(e);
      setInstallResult({ status: "error", message: e instanceof Error ? e.message : "Installation failed." });
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
      setUninstallResult({ status: "error", message: e instanceof Error ? e.message : "Uninstall failed." });
    } finally {
      setUninstalling(false);
    }
  };

  const handleFramegenBackendChange = async (nextBackend: string) => {
    const previousBackend = framegenBackend;
    setFramegenBackendValue(nextBackend);
    setFramegenBackendTouched(true);
    if (pathExists !== true) return;

    try {
      setSwitchingBackend(true);
      const result = await setFramegenBackend(nextBackend);
      if (result.status !== "success") {
        throw new Error(result.message || result.output || "Failed to update the frame-generation backend.");
      }
      setFramegenBackendValue(result.framegen_backend || nextBackend);
      setFramegenBackendTouched(false);
    } catch (error) {
      console.error(error);
      setFramegenBackendValue(previousBackend);
      setFramegenBackendTouched(false);
    } finally {
      setSwitchingBackend(false);
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
        throw new Error(result.message || result.output || "Failed to switch default FSR4 runtime.");
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
          label="Default FSR4 runtime"
          description={FSR4_VARIANT_OPTIONS.find((option) => option.value === fsr4Variant)?.hint}
          menuLabel="Default FSR4 runtime"
          selectedOption={fsr4Variant}
          rgOptions={FSR4_VARIANT_OPTIONS.map((option) => ({ data: option.value, label: option.label }))}
          disabled={installing || uninstalling || switchingVariant || switchingBackend}
          onChange={(option) => {
            void handleFsr4VariantChange(String(option.data));
          }}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <DropdownItem
          layout="below"
          label="Frame generation backend"
          description={FRAMEGEN_BACKEND_OPTIONS.find((option) => option.value === framegenBackend)?.hint}
          menuLabel="Frame generation backend"
          selectedOption={framegenBackend}
          rgOptions={FRAMEGEN_BACKEND_OPTIONS.map((option) => ({ data: option.value, label: option.label }))}
          disabled={installing || uninstalling || switchingBackend}
          onChange={(option) => {
            void handleFramegenBackendChange(String(option.data));
          }}
        />
      </PanelSectionRow>

      {pathExists === true && fgmodInfo?.version && installedVariantLabel && (
        <PanelSectionRow>
          <Field label="Installed bundle" description={`OptiScaler ${fgmodInfo.version}`}>
            {installedVariantLabel}
          </Field>
        </PanelSectionRow>
      )}

      {pathExists === true && (
        <PanelSectionRow>
          <DropdownItem
            layout="below"
            label="Proxy DLL name"
            description={PROXY_DLL_OPTIONS.find((o) => o.value === dllName)?.hint}
            menuLabel="Proxy DLL name"
            selectedOption={dllName}
            rgOptions={PROXY_DLL_OPTIONS.map((o) => ({ data: o.value, label: o.label }))}
            onChange={(option) => setDllName(String(option.data))}
          />
        </PanelSectionRow>
      )}

      {pathExists === true && (
        <SteamGamePatcher dllName={dllName} fsr4Variant={fsr4Variant} framegenBackend={framegenBackend} />
      )}

      <ClipboardCommands pathExists={pathExists} dllName={dllName} />

      {pathExists === true && (
        <PanelSectionRow>
          <ToggleField
            label="Manual Mode"
            description="Show wrapper command clipboard buttons for patching and unpatching through ~/fgmod scripts."
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
        framegenBackend={framegenBackend}
      />

      <ResultDisplay result={installResult} />
      <ResultDisplay result={uninstallResult} />

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

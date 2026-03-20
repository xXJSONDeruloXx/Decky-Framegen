import { useEffect, useState } from "react";
import { PanelSection } from "@decky/ui";
import { runInstallFGMod, runUninstallFGMod } from "../api";
import { OperationResult } from "./ResultDisplay";
import { createAutoCleanupTimer } from "../utils";
import { TIMEOUTS } from "../utils/constants";
import { InstallationStatus } from "./InstallationStatus";
import { OptiScalerHeader } from "./OptiScalerHeader";
import { ClipboardCommands } from "./ClipboardCommands";
import { InstructionCard } from "./InstructionCard";
import { OptiScalerWiki } from "./OptiScalerWiki";
import { UninstallButton } from "./UninstallButton";
import { InstalledGamesSection } from "./InstalledGamesSection";

interface OptiScalerControlsProps {
  pathExists: boolean | null;
  setPathExists: (exists: boolean | null) => void;
}

export function OptiScalerControls({ pathExists, setPathExists }: OptiScalerControlsProps) {
  const [installing, setInstalling] = useState(false);
  const [uninstalling, setUninstalling] = useState(false);
  const [installResult, setInstallResult] = useState<OperationResult | null>(null);
  const [uninstallResult, setUninstallResult] = useState<OperationResult | null>(null);

  useEffect(() => {
    if (!installResult) return () => {};
    return createAutoCleanupTimer(() => setInstallResult(null), TIMEOUTS.resultDisplay);
  }, [installResult]);

  useEffect(() => {
    if (!uninstallResult) return () => {};
    return createAutoCleanupTimer(() => setUninstallResult(null), TIMEOUTS.resultDisplay);
  }, [uninstallResult]);

  const handleInstallClick = async () => {
    try {
      setInstalling(true);
      const result = await runInstallFGMod();
      setInstallResult(result);
      if (result.status === "success") {
        setPathExists(true);
      }
    } catch (error) {
      console.error(error);
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
    } catch (error) {
      console.error(error);
    } finally {
      setUninstalling(false);
    }
  };

  return (
    <PanelSection>
      <InstallationStatus pathExists={pathExists} installing={installing} onInstallClick={handleInstallClick} />
      <OptiScalerHeader pathExists={pathExists} />
      <InstalledGamesSection isAvailable={pathExists === true} />
      <ClipboardCommands pathExists={pathExists} />
      <InstructionCard pathExists={pathExists} />
      <OptiScalerWiki pathExists={pathExists} />
      <UninstallButton pathExists={pathExists} uninstalling={uninstalling} onUninstallClick={handleUninstallClick} />
    </PanelSection>
  );
}

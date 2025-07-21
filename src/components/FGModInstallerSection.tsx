import { useState, useEffect } from "react";
import { PanelSection, PanelSectionRow, ButtonItem } from "@decky/ui";
import { runInstallFGMod, runUninstallFGMod } from "../api";
import { OperationResult } from "./ResultDisplay";
import { SmartClipboardButton } from "./SmartClipboardButton";
import { createAutoCleanupTimer } from "../utils";
import { TIMEOUTS, MESSAGES, STYLES } from "../utils/constants";

interface FGModInstallerSectionProps {
  pathExists: boolean | null;
  setPathExists: (exists: boolean | null) => void;
}

export function FGModInstallerSection({ pathExists, setPathExists }: FGModInstallerSectionProps) {
  const [installing, setInstalling] = useState(false);
  const [uninstalling, setUninstalling] = useState(false);
  const [installResult, setInstallResult] = useState<OperationResult | null>(null);
  const [uninstallResult, setUninstallResult] = useState<OperationResult | null>(null);

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

  const handleInstallClick = async () => {
    try {
      setInstalling(true);
      const result = await runInstallFGMod();
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

  return (
    <PanelSection>
      {pathExists !== null ? (
        <PanelSectionRow>
          <div style={pathExists ? STYLES.statusInstalled : STYLES.statusNotInstalled}>
            {pathExists ? MESSAGES.modInstalled : MESSAGES.modNotInstalled}
          </div>
        </PanelSectionRow>
      ) : null}
      
      {pathExists === false ? (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={handleInstallClick} disabled={installing}>
            {installing ? MESSAGES.installing : MESSAGES.installButton}
          </ButtonItem>
        </PanelSectionRow>
      ) : null}
      
      {pathExists === true ? (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={handleUninstallClick} disabled={uninstalling}>
            {uninstalling ? MESSAGES.uninstalling : MESSAGES.uninstallButton}
          </ButtonItem>
        </PanelSectionRow>
      ) : null}
      
      {pathExists === true ? (
        <PanelSectionRow>
          <div style={STYLES.instructionCard}>
            <div style={{ fontWeight: 'bold', marginBottom: '8px', color: 'var(--decky-accent-text)' }}>
              {MESSAGES.instructionTitle}
            </div>
            <div style={{ whiteSpace: 'pre-line' }}>
              {MESSAGES.instructionText}
            </div>
          </div>
        </PanelSectionRow>
      ) : null}
      
      {pathExists === true ? (
        <SmartClipboardButton />
      ) : null}
    </PanelSection>
  );
}

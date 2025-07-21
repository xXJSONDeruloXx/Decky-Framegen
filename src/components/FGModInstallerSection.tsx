import { useState, useEffect } from "react";
import { PanelSection, PanelSectionRow, ButtonItem } from "@decky/ui";
import { checkFGModPath, runInstallFGMod, runUninstallFGMod } from "../api";
import { ResultDisplay, OperationResult } from "./ResultDisplay";
import { createAutoCleanupTimer, safeAsyncOperation } from "../utils";
import { TIMEOUTS, MESSAGES, STYLES } from "../utils/constants";

export function FGModInstallerSection() {
  const [installing, setInstalling] = useState(false);
  const [uninstalling, setUninstalling] = useState(false);
  const [installResult, setInstallResult] = useState<OperationResult | null>(null);
  const [uninstallResult, setUninstallResult] = useState<OperationResult | null>(null);
  const [pathExists, setPathExists] = useState<boolean | null>(null);

  useEffect(() => {
    const checkPath = async () => {
      const result = await safeAsyncOperation(
        async () => await checkFGModPath(),
        'useEffect -> checkPath'
      );
      if (result) setPathExists(result.exists);
    };
    
    checkPath(); // Initial check
    const intervalId = setInterval(checkPath, TIMEOUTS.pathCheck); // Check every 3 seconds
    return () => clearInterval(intervalId); // Cleanup interval on component unmount
  }, []);

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
          <div style={{ display: 'flex', justifyContent: 'center', width: '100%' }}>
            <div style={pathExists ? STYLES.statusInstalled : STYLES.statusNotInstalled}>
              {pathExists ? MESSAGES.modInstalled : MESSAGES.modNotInstalled}
            </div>
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
      
      <ResultDisplay result={installResult} />
      <ResultDisplay result={uninstallResult} />
      
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
    </PanelSection>
  );
}

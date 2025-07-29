import { useState, useEffect } from "react";
import { PanelSection, PanelSectionRow, ButtonItem } from "@decky/ui";
import { FaBook } from "react-icons/fa";
import { runInstallFGMod, runUninstallFGMod } from "../api";
import { OperationResult } from "./ResultDisplay";
import { SmartClipboardButton } from "./SmartClipboardButton";
import { createAutoCleanupTimer } from "../utils";
import { TIMEOUTS, MESSAGES, STYLES } from "../utils/constants";
import optiScalerImage from "../../assets/optiscaler.png";

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
      {pathExists === false ? (
        <PanelSectionRow>
          <div style={STYLES.statusNotInstalled}>
            {MESSAGES.modNotInstalled}
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
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            marginBottom: '16px' 
          }}>
            <img 
              src={optiScalerImage} 
              alt="OptiScaler" 
              style={{ 
                maxWidth: '100%', 
                height: 'auto',
                borderRadius: '8px'
              }} 
            />
          </div>
        </PanelSectionRow>
      ) : null}
      
      {pathExists === true ? (
        <SmartClipboardButton 
          command="~/fgmod/fgmod %command%"
          buttonText="Copy Patch Command"
        />
      ) : null}
      
      {pathExists === true ? (
        <SmartClipboardButton 
          command="~/fgmod/fgmod-uninstaller.sh %command%"
          buttonText="Copy Unpatch Command"
        />
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
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={() => window.open("https://github.com/optiscaler/OptiScaler/wiki", "_blank")}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <FaBook />
              <div>OptiScaler Wiki</div>
            </div>
          </ButtonItem>
        </PanelSectionRow>
      ) : null}
      
      {pathExists === true ? (
        <PanelSectionRow>
          <ButtonItem 
            layout="below" 
            onClick={handleUninstallClick} 
            disabled={uninstalling}
          >
            <div style={{ 
              color: '#ef4444',
              fontWeight: 'bold'
            }}>
              {uninstalling ? MESSAGES.uninstalling : MESSAGES.uninstallButton}
            </div>
          </ButtonItem>
        </PanelSectionRow>
      ) : null}
    </PanelSection>
  );
}

import { PanelSectionRow, ButtonItem } from "@decky/ui";
import { MESSAGES, STYLES } from "../utils/constants";

interface InstallationStatusProps {
  pathExists: boolean | null;
  installing: boolean;
  onInstallClick: () => void;
}

export function InstallationStatus({ pathExists, installing, onInstallClick }: InstallationStatusProps) {
  if (pathExists !== false) return null;

  return (
    <>
      <PanelSectionRow>
        <div style={STYLES.statusNotInstalled}>
          {MESSAGES.modNotInstalled}
        </div>
      </PanelSectionRow>
      
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={onInstallClick} disabled={installing}>
          {installing ? MESSAGES.installing : MESSAGES.installButton}
        </ButtonItem>
      </PanelSectionRow>
    </>
  );
}

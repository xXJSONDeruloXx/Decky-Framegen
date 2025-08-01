import { PanelSectionRow, ButtonItem } from "@decky/ui";
import { MESSAGES } from "../utils/constants";

interface UninstallButtonProps {
  pathExists: boolean | null;
  uninstalling: boolean;
  onUninstallClick: () => void;
}

export function UninstallButton({ pathExists, uninstalling, onUninstallClick }: UninstallButtonProps) {
  if (pathExists !== true) return null;

  return (
    <PanelSectionRow>
      <ButtonItem 
        layout="below" 
        onClick={onUninstallClick} 
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
  );
}

import { PanelSectionRow, ButtonItem } from "@decky/ui";
import { MESSAGES, STYLES } from "../utils/constants";

interface InstallationStatusProps {
  pathExists: boolean | null;
  installing: boolean;
  onInstallClick: () => void;
  /** ~/fgmod was prepared by an older plugin build and lacks the current injector. */
  bundleOutdated?: boolean;
}

export function InstallationStatus({ pathExists, installing, onInstallClick, bundleOutdated = false }: InstallationStatusProps) {
  if (pathExists === true && bundleOutdated) {
    return (
      <>
        <PanelSectionRow>
          <div style={STYLES.statusNotInstalled}>
            {MESSAGES.bundleOutdated}
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={onInstallClick} disabled={installing}>
            {installing ? MESSAGES.installing : MESSAGES.updateBundleButton}
          </ButtonItem>
        </PanelSectionRow>
      </>
    );
  }

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

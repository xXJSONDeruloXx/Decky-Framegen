// Common types for the application

export interface ResultType {
  status: string;
  message?: string;
  output?: string;
}

export interface GameType {
  appid: number;
  name: string;
}

// Common style definitions
export const STYLES = {
  resultBox: {
    padding: '12px',
    marginTop: '16px',
    backgroundColor: 'var(--decky-selected-ui-bg)',
    borderRadius: '8px',
    border: '1px solid var(--decky-border-color)',
    fontSize: '14px'
  },
  statusInstalled: { 
    color: '#22c55e',
    fontWeight: 'bold',
    fontSize: '14px'
  },
  statusNotInstalled: { 
    color: '#f97316',
    fontWeight: 'bold',
    fontSize: '14px'
  },
  statusSuccess: { color: "#22c55e" },
  statusError: { color: "#ef4444" },
  preWrap: { whiteSpace: "pre-wrap" as const },
  instructionCard: {
    padding: '14px',
    backgroundColor: 'var(--decky-selected-ui-bg)',
    borderRadius: '8px',
    border: '1px solid var(--decky-border-color)',
    marginTop: '8px',
    fontSize: '13px',
    lineHeight: '1.4'
  }
};

// Common timeout values
export const TIMEOUTS = {
  resultDisplay: 5000,  // 5 seconds
  pathCheck: 3000       // 3 seconds
};

// Message strings
export const MESSAGES = {
  modInstalled: "✅ OptiScaler Mod Installed",
  modNotInstalled: "❌ OptiScaler Mod Not Installed",
  installing: "Installing OptiScaler...",
  installButton: "Install OptiScaler FG Mod",
  uninstalling: "Removing OptiScaler...",
  uninstallButton: "Uninstall OptiScaler FG Mod",
  installSuccess: "✅ OptiScaler mod installed successfully!",
  uninstallSuccess: "✅ OptiScaler mod removed successfully.",
  instructionTitle: "How to Use:",
  instructionText: "Click 'Copy Patch Command' or 'Copy Unpatch Command', then go to your game's properties, and paste the command into the Launch Options field.\n\nIn-game: Enable DLSS in graphics settings, or assign a back button to keyboard's 'Insert' key for extended OptiScaler options."
};

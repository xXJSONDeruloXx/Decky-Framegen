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
    borderRadius: '4px'
  },
  statusSuccess: { color: "green" },
  statusError: { color: "red" },
  preWrap: { whiteSpace: "pre-wrap" as const }
};

// Common timeout values
export const TIMEOUTS = {
  resultDisplay: 5000,  // 5 seconds
  pathCheck: 3000       // 3 seconds
};

// Message strings
export const MESSAGES = {
  modInstalled: "OptiScaler Mod Is Installed",
  modNotInstalled: "OptiScaler Mod Not Installed",
  installing: "Installing...",
  installButton: "Install OptiScaler FG Mod",
  uninstalling: "Uninstalling...",
  uninstallButton: "Uninstall OptiScaler FG Mod",
  instructionText: "Install the OptiScaler-based mod above, then select and patch a game below to enable DLSS replacement with FSR Frame Generation. Map a button to \"insert\" key to bring up the OptiScaler menu in-game."
};

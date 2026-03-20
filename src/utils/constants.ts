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
  statusSuccess: { color: '#22c55e' },
  statusError: { color: '#ef4444' },
  preWrap: { whiteSpace: 'pre-wrap' as const },
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
  resultDisplay: 5000,
  pathCheck: 3000
};

// Message strings
export const MESSAGES = {
  modInstalled: '✅ Prefix-managed OptiScaler runtime installed',
  modNotInstalled: '❌ Prefix-managed OptiScaler runtime not installed',
  installing: 'Installing prefix-managed runtime...',
  installButton: 'Install Prefix-Managed Runtime',
  uninstalling: 'Removing runtime and cleaning prefixes...',
  uninstallButton: 'Remove Runtime + Clean Prefixes',
  installSuccess: '✅ Prefix-managed OptiScaler runtime installed successfully!',
  uninstallSuccess: '✅ Prefix-managed OptiScaler runtime removed successfully.',
  instructionTitle: 'How it works:',
  instructionText:
    'Use the Steam game integration section to enable OptiScaler for a specific game, or copy the launch command manually.\n\nOn launch, the plugin stages OptiScaler into compatdata/<appid>/pfx/drive_c/windows/system32 and keeps its writable INI under compatdata/<appid>/optiscaler-managed. The game install directory is left untouched.\n\nDefault proxy: winmm.dll. For advanced testing you can override it in launch options, e.g. OPTISCALER_PROXY=dxgi ~/fgmod/fgmod %command%.\n\nIn-game: press Insert to open the OptiScaler menu.'
};

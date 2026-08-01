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

// Proxy DLL name options for OptiScaler injection
export const PROXY_DLL_OPTIONS = [
  { value: "dxgi.dll",       label: "dxgi.dll (default)",  hint: "Works for most DX12 games. Default." },
  { value: "winmm.dll",      label: "winmm.dll",      hint: "Use when dxgi.dll conflicts with an existing game file." },
  { value: "version.dll",    label: "version.dll",    hint: "Common fallback; works well with many launchers." },
  { value: "dbghelp.dll",    label: "dbghelp.dll",    hint: "Use for debug helper hook paths." },
  { value: "winhttp.dll",    label: "winhttp.dll",    hint: "Use when other DLL names conflict." },
  { value: "wininet.dll",    label: "wininet.dll",    hint: "Use when other DLL names conflict." },
  { value: "OptiScaler.asi", label: "OptiScaler.asi", hint: "For ASI loaders. Requires an ASI loader already installed in the game." },
] as const;

export type ProxyDllValue = typeof PROXY_DLL_OPTIONS[number]["value"];
export const DEFAULT_PROXY_DLL: ProxyDllValue = "dxgi.dll";

export const FSR4_VARIANT_OPTIONS = [
  {
    value: "rdna23-int8",
    label: "4.0.2c | RDNA2/3 Compatibility",
    hint: "Older compatible runtime for RDNA2/3. In most cases, use the Valve 4.1.1 path for RDNA2 or the regular 4.1.1 driver override.",
  },
  {
    value: "rdna4-native",
    label: "4.1.1 | FFX 2.3 SDK",
    hint: "Uses OptiScaler 0.9.4's bundled FSR4.1.1 SDK upscaler. Official FSR4 support is RDNA4 (FP8) and RDNA3 desktop GPUs (INT8).",
  },
  {
    value: "rdna34-official-411",
    label: "4.1.1 | Driver Override",
    hint: "Uses the final bundled FSR4.1.1 SDK upscaler plus the separately bundled 4.1.1 amdxcffx64.dll driver override.",
  },
  {
    value: "rdna2-valve-411-pre10",
    label: "4.1.1 | Valve RDNA2 Compatibility",
    hint: "Uses the final bundled FSR4.1.1 SDK upscaler with the existing pre10 injector, Valve 4.1.1 amdxcffx64.dll, amdxc64.dll, and RDNA2-specific INI overrides.",
  },
] as const;

export type Fsr4VariantValue = typeof FSR4_VARIANT_OPTIONS[number]["value"];
export const DEFAULT_FSR4_VARIANT: Fsr4VariantValue = "rdna23-int8";

export const FRAMEGEN_BACKEND_OPTIONS = [
  {
    value: "auto",
    label: "OptiScaler automatic selection",
    hint: "Let OptiScaler select the compatible frame-generation path.",
  },
  {
    value: "nukems",
    label: "Nukem's DLSSG → FSR3",
    hint: "Use Nukem's DLSSG-to-FSR3 path for games that need it.",
  },
] as const;

export type FramegenBackendValue = typeof FRAMEGEN_BACKEND_OPTIONS[number]["value"];
export const DEFAULT_FRAMEGEN_BACKEND: FramegenBackendValue = "auto";

// Common timeout values
export const TIMEOUTS = {
  resultDisplay: 5000,  // 5 seconds
  pathCheck: 3000       // 3 seconds
};

// Message strings
export const MESSAGES = {
  modInstalled: "OptiScaler Mod Installed",
  modNotInstalled: "OptiScaler Mod Not Installed",
  installing: "Installing OptiScaler...",
  installButton: "Setup OptiScaler Mod",
  uninstalling: "Removing OptiScaler...",
  uninstallButton: "Remove OptiScaler Mod",
  installSuccess: "OptiScaler mod setup successfully!",
  uninstallSuccess: "OptiScaler mod removed successfully.",
  instructionTitle: "How to Use:",
  instructionText: "Use 'Copy launch options' for the standard direct launch-options method. If you want the wrapper commands instead, enable Manual Mode to reveal 'Copy Patch Command' and 'Copy Unpatch Command'.\n\nIn-game: Enable DLSS in graphics settings to unlock FSR 3.1/XeSS 2.0 in DirectX12 Games.\n\nFor extended OptiScaler options, assign a back button to a keyboard's 'Insert' key."
};

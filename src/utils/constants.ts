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
    hint: "Valve 4.1.1 amdxcffx64.dll + amdxc64.dll with the OptiScaler v10 nightly injector (2026-09-05). Its overlay opens with Insert but ignores the mouse on Steam Deck; prefer the 0.9.4-injector variant.",
  },
  {
    value: "rdna2-valve-411-094",
    label: "4.1.1 | Valve RDNA2 (0.9.4 injector)",
    hint: "Steam Deck default. Valve 4.1.1 amdxcffx64.dll + amdxc64.dll injected by OptiScaler 0.9.4 (working overlay), INT8 forced, DX12 upscaler preset to FSR 3.1→4 so FSR 4.1.1 is active without opening the overlay.",
  },
] as const;

export type Fsr4VariantValue = typeof FSR4_VARIANT_OPTIONS[number]["value"];
export const DEFAULT_FSR4_VARIANT: Fsr4VariantValue = "rdna2-valve-411-094";

// Per-game choices (stored in the FRAMEGEN_PATCH marker, applied on Patch/Reinstall)
export const DX12_UPSCALER_OPTIONS = [
  { value: "auto", label: "Runtime default" },
  { value: "fsr4", label: "FSR 3.1 → FSR 4" },
  { value: "xess", label: "XeSS" },
  { value: "fsr22", label: "FSR 2.2" },
] as const;

export const FRAME_GENERATION_OPTIONS = [
  { value: "default", label: "Game's DLSS FG → Nukem's (default)" },
  { value: "optifg", label: "OptiFG (experimental, games without DLSS FG)" },
] as const;

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
  bundleOutdated: "Installed OptiScaler bundle is from an older plugin version. Update it, then re-patch your games.",
  updateBundleButton: "Update OptiScaler bundle",
  instructionTitle: "How to Use:",
  instructionText: "Pick a game under 'Steam game' and press the Patch button: the plugin copies OptiScaler into the game folder and sets the Steam launch options for you. 'Copy launch options' only re-copies those launch options (for example if Steam lost them); it does not patch anything. Manual Mode exposes the older ~/fgmod wrapper commands instead.\n\nIn-game: enable DLSS in the graphics settings to unlock FSR 3.1/XeSS in DirectX 12 games.\n\nFor the OptiScaler overlay, bind a back button to the keyboard 'Insert' key."
};

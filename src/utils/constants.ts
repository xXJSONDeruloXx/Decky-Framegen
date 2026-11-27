// Common types for the application
import { L } from "./i18n";

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
  { value: "dxgi.dll",       label: L("dxgi.dll (default)", "dxgi.dll（預設）"),  hint: L("Works for most DX12 games. Default.", "適用於多數 DX12 遊戲，建議預設使用。") },
  { value: "winmm.dll",      label: "winmm.dll",      hint: L("Use when dxgi.dll conflicts with an existing game file.", "當 dxgi.dll 與現有遊戲檔案衝突時使用。") },
  { value: "version.dll",    label: "version.dll",    hint: L("Common fallback; works well with many launchers.", "常見備援選項，相容於多數啟動器。") },
  { value: "dbghelp.dll",    label: "dbghelp.dll",    hint: L("Use for debug helper hook paths.", "適用於除錯輔助程式庫掛鉤路徑。") },
  { value: "winhttp.dll",    label: "winhttp.dll",    hint: L("Use when other DLL names conflict.", "當其他 DLL 名稱衝突時使用。") },
  { value: "wininet.dll",    label: "wininet.dll",    hint: L("Use when other DLL names conflict.", "當其他 DLL 名稱衝突時使用。") },
  { value: "OptiScaler.asi", label: "OptiScaler.asi", hint: L("For ASI loaders. Requires an ASI loader already installed in the game.", "適用於 ASI 載入器，遊戲內需已安裝 ASI Loader。") },
] as const;

export type ProxyDllValue = typeof PROXY_DLL_OPTIONS[number]["value"];
export const DEFAULT_PROXY_DLL: ProxyDllValue = "dxgi.dll";

export const FSR4_VARIANT_OPTIONS = [
  {
    value: "rdna23-int8",
    label: L("4.0.2c | RDNA2/3 Compatibility", "4.0.2c | RDNA2/3 相容版"),
    hint: L(
      "Older compatible runtime for RDNA2/3. In most cases, use the Valve 4.1.1 path for RDNA2 or the regular 4.1.1 driver override.",
      "較舊的 RDNA2/3 相容執行環境。多數情況下，RDNA2 建議使用 Valve 4.1.1 路徑或一般 4.1.1 驅動覆寫。",
    ),
  },
  {
    value: "rdna4-native",
    label: "4.1.1 | FFX 2.3 SDK",
    hint: L(
      "Uses OptiScaler 0.9.4's bundled FSR4.1.1 SDK upscaler. Official FSR4 support is RDNA4 (FP8) and RDNA3 desktop GPUs (INT8).",
      "使用 OptiScaler 0.9.4 隨附的 FSR4.1.1 SDK 升頻器。官方 FSR4 支援為 RDNA4 (FP8) 與 RDNA3 桌上型 GPU (INT8)。",
    ),
  },
  {
    value: "rdna34-official-411",
    label: L("4.1.1 | Driver Override", "4.1.1 | 驅動程式覆寫"),
    hint: L(
      "Uses the final bundled FSR4.1.1 SDK upscaler plus the separately bundled 4.1.1 amdxcffx64.dll driver override.",
      "使用最終隨附的 FSR4.1.1 SDK 升頻器搭配獨立的 4.1.1 amdxcffx64.dll 驅動覆寫。",
    ),
  },
  {
    value: "rdna2-valve-411-pre10",
    label: L("4.1.1 | Valve RDNA2 Compatibility", "4.1.1 | Valve RDNA2 相容版"),
    hint: L(
      "Uses the final bundled FSR4.1.1 SDK upscaler with the existing pre10 injector, Valve 4.1.1 amdxcffx64.dll, amdxc64.dll, and RDNA2-specific INI overrides.",
      "使用最終隨附的 FSR4.1.1 SDK 升頻器搭配 pre10 注入器、Valve 4.1.1 amdxcffx64.dll、amdxc64.dll 與 RDNA2 專用 INI 覆寫。",
    ),
  },
] as const;

export type Fsr4VariantValue = typeof FSR4_VARIANT_OPTIONS[number]["value"];
export const DEFAULT_FSR4_VARIANT: Fsr4VariantValue = "rdna23-int8";

// Common timeout values
export const TIMEOUTS = {
  resultDisplay: 5000,  // 5 seconds
  pathCheck: 3000       // 3 seconds
};

// Message strings
export const MESSAGES = {
  modInstalled: L("OptiScaler Mod Installed", "OptiScaler 模組已安裝"),
  modNotInstalled: L("OptiScaler Mod Not Installed", "尚未安裝 OptiScaler 模組"),
  installing: L("Installing OptiScaler...", "正在安裝 OptiScaler..."),
  installButton: L("Setup OptiScaler Mod", "安裝 OptiScaler 模組"),
  uninstalling: L("Removing OptiScaler...", "正在移除 OptiScaler..."),
  uninstallButton: L("Remove OptiScaler Mod", "移除 OptiScaler 模組"),
  installSuccess: L("OptiScaler mod setup successfully!", "OptiScaler 模組設定完成！"),
  uninstallSuccess: L("OptiScaler mod removed successfully.", "OptiScaler 模組已成功移除。"),
  instructionTitle: L("How to Use:", "使用說明："),
  instructionText: L(
    "Use 'Copy launch options' for the standard direct launch-options method. If you want the wrapper commands instead, enable Manual Mode to reveal 'Copy Patch Command' and 'Copy Unpatch Command'.\n\nIn-game: Enable DLSS in graphics settings to unlock FSR 3.1/XeSS 2.0 in DirectX12 Games.\n\nFor extended OptiScaler options, assign a back button to a keyboard's 'Insert' key.",
    "一般情況請使用「複製啟動選項」直接套用標準啟動參數。若需使用包裝腳本指令，請開啟手動模式以顯示「複製修補指令」與「複製還原指令」。\n\n遊戲內設定：在顯示設定中開啟 DLSS，即可於 DirectX 12 遊戲解鎖 FSR 3.1 / XeSS 2.0。\n\n若要開啟進階 OptiScaler 選單，請將手把背鍵指定為鍵盤的「Insert」鍵。",
  )
};

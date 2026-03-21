// Common types used throughout the application

export interface ApiResponse {
  status: string;
  message?: string;
  output?: string;
  live_applied?: boolean;
  proxy?: string;
}

export interface GameInfo {
  appid: string | number;
  name: string;
}

export interface GameConfigPaths {
  compatdata: string;
  managed_root: string;
  managed_ini: string;
  system32: string;
  live_ini: string;
}

export interface GameConfigResponse extends ApiResponse {
  appid?: string;
  name?: string;
  proxy?: string;
  settings?: Record<string, string>;
  raw_ini?: string;
  managed_exists?: boolean;
  live_available?: boolean;
  paths?: GameConfigPaths;
}

export interface LaunchOptions {
  command: string;
  arguments?: string[];
}

export interface ModInstallationConfig {
  files: string[];
  paths: {
    fgmod: string;
    assets: string;
    bin: string;
  };
}

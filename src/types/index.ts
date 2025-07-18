// Common types used throughout the application

export interface ApiResponse {
  status: string;
  message?: string;
  output?: string;
}

export interface GameInfo {
  appid: string | number;
  name: string;
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

declare module "*.svg" {
  const content: string;
  export default content;
}

declare module "*.png" {
  const content: string;
  export default content;
}

declare module "*.jpg" {
  const content: string;
  export default content;
}

declare const SteamClient: {
  Apps: {
    RegisterForAppDetails(
      appId: number,
      callback: (details: { strLaunchOptions?: string }) => void
    ): { unregister: () => void };
    SetAppLaunchOptions(appId: number, options: string): void;
  };
};

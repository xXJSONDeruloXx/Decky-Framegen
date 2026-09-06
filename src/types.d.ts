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

// `SteamClient` is declared globally by @decky/ui; a second declaration here
// made `tsc --noEmit` fail (TS2451) while rollup silently ignored it.

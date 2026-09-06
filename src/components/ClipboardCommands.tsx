import { SmartClipboardButton } from "./SmartClipboardButton";

interface ClipboardCommandsProps {
  pathExists: boolean | null;
  dllName: string;
  manualModeEnabled?: boolean;
  showLaunchOptions?: boolean;
}

export function ClipboardCommands({
  pathExists,
  dllName,
  manualModeEnabled = false,
  showLaunchOptions = true,
}: ClipboardCommandsProps) {
  if (pathExists !== true) return null;

  const launchCmd =
    dllName === "OptiScaler.asi"
      ? "SteamDeck=0 %command%"
      : `WINEDLLOVERRIDES=${dllName.replace(".dll", "")}=n,b SteamDeck=0 %command%`;

  // fgmod.sh reads the proxy name from $DLL (default dxgi.dll); keep the default string unchanged.
  const patchCmd =
    dllName === "dxgi.dll" ? "~/fgmod/fgmod %command%" : `DLL=${dllName} ~/fgmod/fgmod %command%`;

  return (
    <>
      {showLaunchOptions ? (
        <SmartClipboardButton
          command={launchCmd}
          buttonText="Copy launch options"
        />
      ) : null}
      {manualModeEnabled ? (
        <>
          <SmartClipboardButton
            command={patchCmd}
            buttonText="Copy Patch Command"
          />
          <SmartClipboardButton
            command="~/fgmod/fgmod-uninstaller.sh %command%"
            buttonText="Copy Unpatch Command"
          />
        </>
      ) : null}
    </>
  );
}

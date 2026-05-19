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
            command="~/fgmod/fgmod %command%"
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

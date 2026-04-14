import { SmartClipboardButton } from "./SmartClipboardButton";

interface ClipboardCommandsProps {
  pathExists: boolean | null;
  dllName: string;
}

export function ClipboardCommands({ pathExists, dllName }: ClipboardCommandsProps) {
  if (pathExists !== true) return null;

  const launchCmd =
    dllName === "OptiScaler.asi"
      ? "SteamDeck=0 %command%"
      : `WINEDLLOVERRIDES=${dllName.replace(".dll", "")}=n,b SteamDeck=0 %command%`;

  return (
    <SmartClipboardButton
      command={launchCmd}
      buttonText="Copy launch options"
    />
  );
}

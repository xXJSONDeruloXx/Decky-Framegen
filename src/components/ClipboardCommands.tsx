import { SmartClipboardButton } from "./SmartClipboardButton";
import { L } from "../utils/i18n";

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
          buttonText={L("Copy launch options", "複製啟動選項")}
        />
      ) : null}
      {manualModeEnabled ? (
        <>
          <SmartClipboardButton
            command="~/fgmod/fgmod %command%"
            buttonText={L("Copy Patch Command", "複製修補指令")}
          />
          <SmartClipboardButton
            command="~/fgmod/fgmod-uninstaller.sh %command%"
            buttonText={L("Copy Unpatch Command", "複製還原指令")}
          />
        </>
      ) : null}
    </>
  );
}

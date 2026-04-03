import { SmartClipboardButton } from "./SmartClipboardButton";
import { DEFAULT_PROXY_DLL } from "../utils/constants";

interface ClipboardCommandsProps {
  pathExists: boolean | null;
  dllName: string;
}

export function ClipboardCommands({ pathExists, dllName }: ClipboardCommandsProps) {
  if (pathExists !== true) return null;

  const launchCommand =
    dllName === DEFAULT_PROXY_DLL
      ? "~/fgmod/fgmod %command%"
      : `DLL=${dllName} ~/fgmod/fgmod %command%`;

  return (
    <>
      <SmartClipboardButton
        command={launchCommand}
        buttonText="Copy Patch Command"
      />

      <SmartClipboardButton
        command="~/fgmod/fgmod-uninstaller.sh %command%"
        buttonText="Copy Unpatch Command"
      />
    </>
  );
}

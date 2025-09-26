import { SmartClipboardButton } from "./SmartClipboardButton";
import type { CustomOverrideConfig } from "../types/index";

interface ClipboardCommandsProps {
  pathExists: boolean | null;
  overrideConfig?: CustomOverrideConfig | null;
}

export function ClipboardCommands({ pathExists, overrideConfig }: ClipboardCommandsProps) {
  if (pathExists !== true) return null;

  const patchCommand = overrideConfig
    ? `${overrideConfig.envAssignment} ~/fgmod/fgmod %command%`
    : "~/fgmod/fgmod %command%";

  return (
    <>
      <SmartClipboardButton 
        command={patchCommand}
        buttonText="Copy Patch Command"
      />
      
      <SmartClipboardButton 
        command="~/fgmod/fgmod-uninstaller.sh %command%"
        buttonText="Copy Unpatch Command"
      />
    </>
  );
}

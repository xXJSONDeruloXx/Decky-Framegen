import { SmartClipboardButton } from "./SmartClipboardButton";

interface ClipboardCommandsProps {
  pathExists: boolean | null;
}

export function ClipboardCommands({ pathExists }: ClipboardCommandsProps) {
  if (pathExists !== true) return null;

  return (
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
  );
}

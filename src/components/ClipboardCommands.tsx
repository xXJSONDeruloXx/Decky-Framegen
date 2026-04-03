import { SmartClipboardButton } from "./SmartClipboardButton";

interface ClipboardCommandsProps {
  pathExists: boolean | null;
  dllName: string;
}

export function ClipboardCommands({ pathExists, dllName }: ClipboardCommandsProps) {
  if (pathExists !== true) return null;

  return (
    <>
      <SmartClipboardButton
        command={`DLL=${dllName} ~/fgmod/fgmod %command%`}
        buttonText="Copy Patch Command"
      />

      <SmartClipboardButton
        command="~/fgmod/fgmod-uninstaller.sh %command%"
        buttonText="Copy Unpatch Command"
      />
    </>
  );
}

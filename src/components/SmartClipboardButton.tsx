import { useEffect, useState } from "react";
import { ButtonItem, PanelSectionRow } from "@decky/ui";
import { toaster } from "@decky/api";
import { FaCheck, FaClipboard } from "react-icons/fa";

interface SmartClipboardButtonProps {
  command?: string;
  buttonText?: string;
}

export function SmartClipboardButton({
  command = "~/fgmod/fgmod %command%",
  buttonText = "Copy Launch Command",
}: SmartClipboardButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  useEffect(() => {
    if (!showSuccess) return undefined;
    const timer = setTimeout(() => setShowSuccess(false), 3000);
    return () => clearTimeout(timer);
  }, [showSuccess]);

  const performCopy = async () => {
    if (isLoading || showSuccess) return;

    setIsLoading(true);
    try {
      const tempInput = document.createElement("input");
      tempInput.value = command;
      tempInput.style.position = "absolute";
      tempInput.style.left = "-9999px";
      document.body.appendChild(tempInput);
      tempInput.focus();
      tempInput.select();

      let copySuccess = false;
      try {
        if (document.execCommand("copy")) {
          copySuccess = true;
        }
      } catch (execError) {
        try {
          await navigator.clipboard.writeText(command);
          copySuccess = true;
        } catch (clipboardError) {
          console.error("Clipboard copy failed", execError, clipboardError);
        }
      }

      document.body.removeChild(tempInput);

      if (!copySuccess) {
        toaster.toast({
          title: "Copy Failed",
          body: "Unable to copy to clipboard",
        });
        return;
      }

      setShowSuccess(true);
    } catch (error) {
      toaster.toast({
        title: "Copy Failed",
        body: `Error: ${String(error)}`,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <PanelSectionRow>
      <ButtonItem layout="below" onClick={performCopy} disabled={isLoading || showSuccess}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {showSuccess ? (
            <FaCheck style={{ color: "#4CAF50" }} />
          ) : isLoading ? (
            <FaClipboard style={{ animation: "pulse 1s ease-in-out infinite", opacity: 0.7 }} />
          ) : (
            <FaClipboard />
          )}
          <div style={{ color: showSuccess ? "#4CAF50" : "inherit", fontWeight: showSuccess ? "bold" : "normal" }}>
            {showSuccess ? "Copied to clipboard" : isLoading ? "Copying..." : buttonText}
          </div>
        </div>
      </ButtonItem>
      <style>{`
        @keyframes pulse {
          0% { opacity: 0.7; }
          50% { opacity: 1; }
          100% { opacity: 0.7; }
        }
      `}</style>
    </PanelSectionRow>
  );
}

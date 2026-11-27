import { useState, useEffect } from "react";
import { PanelSectionRow, ButtonItem, ConfirmModal, showModal } from "@decky/ui";
import { FaClipboard, FaCheck } from "react-icons/fa";
import { toaster } from "@decky/api";
import { L } from "../utils/i18n";

interface SmartClipboardButtonProps {
  command?: string;
  buttonText?: string;
}

export function SmartClipboardButton({ 
  command = "~/fgmod/fgmod %command%",
  buttonText = L("Copy Launch Command", "複製啟動指令")
}: SmartClipboardButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  // Reset success state after 3 seconds
  useEffect(() => {
    if (showSuccess) {
      const timer = setTimeout(() => {
        setShowSuccess(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [showSuccess]);

  const copyToClipboard = async () => {
    if (isLoading || showSuccess) return;
    
    const isPatchCommand = command.includes("fgmod %command%") && !command.includes("uninstaller");
    
    if (isPatchCommand) {
      showModal(
        <ConfirmModal 
          strTitle={L("Patch Game with OptiScaler?", "確定要使用 OptiScaler 修補遊戲？")}
          strDescription={L(
            "WARNING: Decky Framegen does not unpatch games when uninstalled. Be sure to unpatch the game or run the OptiScaler uninstall script inside the game files if you choose to uninstall the plugin or the game has issues.",
            "警告：解除安裝 Decky Framegen 時不會自動還原已修補的遊戲。若未來要移除此插件或遊戲發生異常，請務必先還原該遊戲或在遊戲目錄執行 OptiScaler 解除安裝腳本。",
          )}
          strOKButtonText={L("Copy Patch Command", "複製修補指令")}
          strCancelButtonText={L("Cancel", "取消")}
          onOK={async () => {
            await performCopy();
          }}
        />
      );
      return;
    }
    
    // For non-patch commands, copy directly
    await performCopy();
  };

  const performCopy = async () => {
    if (isLoading || showSuccess) return;
    
    setIsLoading(true);
    try {
      const text = command;
      
      // Use the proven input simulation method
      const tempInput = document.createElement('input');
      tempInput.value = text;
      tempInput.style.position = 'absolute';
      tempInput.style.left = '-9999px';
      document.body.appendChild(tempInput);
      
      // Focus and select the text
      tempInput.focus();
      tempInput.select();
      
      // Try copying using execCommand first (most reliable in gaming mode)
      let copySuccess = false;
      try {
        if (document.execCommand('copy')) {
          copySuccess = true;
        }
      } catch (e) {
        // If execCommand fails, try navigator.clipboard as fallback
        try {
          await navigator.clipboard.writeText(text);
          copySuccess = true;
        } catch (clipboardError) {
          console.error('Both copy methods failed:', e, clipboardError);
        }
      }
      
      // Clean up
      document.body.removeChild(tempInput);
      
      if (copySuccess) {
        // Show success feedback in the button instead of toast
        setShowSuccess(true);
        // Verify the copy worked by reading back
        try {
          const readBack = await navigator.clipboard.readText();
          if (readBack !== text) {
            // Copy worked but verification failed - still show success
            console.log('Copy verification failed but copy likely worked');
          }
        } catch (e) {
          // Verification failed but copy likely worked
          console.log('Copy verification unavailable but copy likely worked');
        }
      } else {
        toaster.toast({
          title: L("Copy Failed", "複製失敗"),
          body: L("Unable to copy to clipboard", "無法複製到剪貼簿")
        });
      }

    } catch (error) {
      toaster.toast({
        title: L("Copy Failed", "複製失敗"),
        body: `${L("Error", "錯誤")}: ${String(error)}`
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <PanelSectionRow>
      <ButtonItem
        layout="below"
        onClick={copyToClipboard}
        disabled={isLoading || showSuccess}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {showSuccess ? (
            <FaCheck style={{ 
              color: "#4CAF50" // Green color for success
            }} />
          ) : isLoading ? (
            <FaClipboard style={{ 
              animation: "pulse 1s ease-in-out infinite",
              opacity: 0.7 
            }} />
          ) : (
            <FaClipboard />
          )}
          <div style={{ 
            color: showSuccess ? "#4CAF50" : "inherit",
            fontWeight: showSuccess ? "bold" : "normal"
          }}>
            {showSuccess ? L("Copied to clipboard", "已複製到剪貼簿") : isLoading ? L("Copying...", "正在複製...") : buttonText}
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

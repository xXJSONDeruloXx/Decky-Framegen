import { logError } from "../api";

/**
 * Utility for creating a timer that automatically clears after specified timeout
 * @param callback Function to call when timer completes
 * @param timeout Timeout in milliseconds
 * @returns Cleanup function that can be used in useEffect
 */
export const createAutoCleanupTimer = (callback: () => void, timeout: number): (() => void) => {
  const timer = setTimeout(callback, timeout);
  return () => clearTimeout(timer);
};

/**
 * Copy text to the clipboard from Gaming Mode: execCommand through a hidden
 * input first (most reliable there), navigator.clipboard as fallback.
 */
export const copyTextToClipboard = async (text: string): Promise<boolean> => {
  const tempInput = document.createElement("textarea");
  tempInput.value = text;
  tempInput.style.position = "absolute";
  tempInput.style.left = "-9999px";
  document.body.appendChild(tempInput);
  tempInput.focus();
  tempInput.select();
  let ok = false;
  try {
    ok = document.execCommand("copy") === true;
  } catch (e) {
    console.error("execCommand copy failed:", e);
  }
  document.body.removeChild(tempInput);
  if (!ok) {
    try {
      await navigator.clipboard.writeText(text);
      ok = true;
    } catch (e) {
      console.error("clipboard.writeText failed:", e);
    }
  }
  return ok;
};

/**
 * Safe wrapper for async operations to handle errors consistently
 * @param operation Async operation to perform
 * @param errorContext Context string for error logging
 */
export const safeAsyncOperation = async <T,>(
  operation: () => Promise<T>, 
  errorContext: string
): Promise<T | undefined> => {
  try {
    return await operation();
  } catch (e) {
    // Best-effort backend logging; must never surface as an unhandled rejection.
    logError(`${errorContext}: ${String(e)}`).catch(() => {});
    console.error(e);
    return undefined;
  }
};

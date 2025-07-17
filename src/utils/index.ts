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
    logError(`${errorContext}: ${String(e)}`);
    console.error(e);
    return undefined;
  }
};

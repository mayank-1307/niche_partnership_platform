const clientLoggingEnabled = import.meta.env.DEV || import.meta.env.VITE_ENABLE_CLIENT_LOGS === "true";

export function debugLog(message: string, meta?: Record<string, unknown>) {
  if (!clientLoggingEnabled) return;
  console.debug(`[client] ${message}`, meta ?? {});
}

export function errorLog(message: string, error: unknown) {
  if (!clientLoggingEnabled) return;
  console.error(`[client] ${message}`, error);
}

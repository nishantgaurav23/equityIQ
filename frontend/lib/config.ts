/**
 * Frontend configuration with environment variable defaults.
 */
export const config = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  appName: process.env.NEXT_PUBLIC_APP_NAME || "EquityIQ",
} as const;

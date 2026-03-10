/**
 * Currency utilities for EquityIQ.
 */

export interface CurrencyInfo {
  code: string;
  symbol: string;
  name: string;
}

export const CURRENCIES: CurrencyInfo[] = [
  { code: "USD", symbol: "$", name: "US Dollar" },
  { code: "INR", symbol: "₹", name: "Indian Rupee" },
  { code: "EUR", symbol: "€", name: "Euro" },
  { code: "GBP", symbol: "£", name: "British Pound" },
  { code: "JPY", symbol: "¥", name: "Japanese Yen" },
  { code: "CAD", symbol: "C$", name: "Canadian Dollar" },
  { code: "AUD", symbol: "A$", name: "Australian Dollar" },
];

export function getCurrencySymbol(code: string): string {
  return CURRENCIES.find((c) => c.code === code)?.symbol ?? code;
}

export function formatPrice(value: number, currency: string): string {
  const sym = getCurrencySymbol(currency);
  if (currency === "JPY") return `${sym}${Math.round(value).toLocaleString()}`;
  return `${sym}${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

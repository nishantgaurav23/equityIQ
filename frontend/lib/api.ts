/**
 * Typed API client for the EquityIQ FastAPI backend.
 */
import { config } from "./config";
import type {
  ChatEvent,
  ChatHistoryResponse,
  ChatRequest,
  FinalVerdict,
  HealthStatus,
  PortfolioInsight,
  SignalSnapshot,
  TickerSearchResult,
} from "@/types/api";

export class ApiError extends Error {
  constructor(
    public statusCode: number,
    public detail: string,
    public errorType?: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${config.apiUrl}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    signal: options?.signal ?? AbortSignal.timeout(90_000),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText, body.error_type);
  }

  return res.json() as Promise<T>;
}

export async function analyzeStock(ticker: string): Promise<FinalVerdict> {
  return request<FinalVerdict>(`/api/v1/analyze/${encodeURIComponent(ticker)}`, {
    method: "POST",
  });
}

export async function searchTickers(
  query: string,
  market: string = "all",
): Promise<TickerSearchResult[]> {
  return request<TickerSearchResult[]>(
    `/api/v1/search?q=${encodeURIComponent(query)}&market=${market}`,
  );
}

export async function getPortfolio(tickers: string[]): Promise<PortfolioInsight> {
  return request<PortfolioInsight>("/api/v1/portfolio", {
    method: "POST",
    body: JSON.stringify({ tickers }),
  });
}

export async function checkHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}

export async function getTickerHistory(
  ticker: string,
  limit?: number,
  offset?: number,
): Promise<FinalVerdict[]> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  const qs = params.toString();
  return request<FinalVerdict[]>(
    `/api/v1/history/${encodeURIComponent(ticker)}${qs ? `?${qs}` : ""}`,
  );
}

export async function getRecentVerdicts(limit?: number): Promise<FinalVerdict[]> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", String(limit));
  const qs = params.toString();
  return request<FinalVerdict[]>(`/api/v1/history${qs ? `?${qs}` : ""}`);
}

export interface PriceHistoryData {
  prices: number[];
  volumes: number[];
  dates: string[];
  currency?: string;
}

export async function getPriceHistory(
  ticker: string,
  days: number = 90,
): Promise<PriceHistoryData> {
  return request<PriceHistoryData>(
    `/api/v1/price-history/${encodeURIComponent(ticker)}?days=${days}`,
  );
}

export async function getMultiPriceHistory(
  tickers: string[],
  days: number = 90,
): Promise<Record<string, PriceHistoryData>> {
  return request<Record<string, PriceHistoryData>>(
    `/api/v1/price-history-multi?tickers=${tickers.map(encodeURIComponent).join(",")}&days=${days}`,
  );
}

export interface ExchangeRate {
  from: string;
  to: string;
  rate: number;
}

export async function getExchangeRate(
  from: string,
  to: string,
): Promise<ExchangeRate> {
  return request<ExchangeRate>(
    `/api/v1/exchange-rate?from_currency=${from}&to_currency=${to}`,
  );
}

// Chat API (S16.2)
export async function* streamChat(
  chatRequest: ChatRequest,
): AsyncGenerator<ChatEvent> {
  const url = `${config.apiUrl}/api/v1/chat`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(chatRequest),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText, body.error_type);
  }

  const reader = res.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          yield JSON.parse(line.slice(6)) as ChatEvent;
        } catch {
          // skip malformed SSE lines
        }
      }
    }
  }
}

export async function getChatHistory(
  sessionId: string,
  limit?: number,
): Promise<ChatHistoryResponse> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", String(limit));
  const qs = params.toString();
  return request<ChatHistoryResponse>(
    `/api/v1/chat/history/${encodeURIComponent(sessionId)}${qs ? `?${qs}` : ""}`,
  );
}

export async function deleteChatHistory(sessionId: string): Promise<void> {
  await request<{ deleted: boolean }>(
    `/api/v1/chat/history/${encodeURIComponent(sessionId)}`,
    { method: "DELETE" },
  );
}

export async function getSignalTrend(
  ticker: string,
  limit?: number,
): Promise<SignalSnapshot[]> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", String(limit));
  const qs = params.toString();
  return request<SignalSnapshot[]>(
    `/api/v1/history/${encodeURIComponent(ticker)}/trend${qs ? `?${qs}` : ""}`,
  );
}

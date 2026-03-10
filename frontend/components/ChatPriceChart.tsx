"use client";

import { useState, useEffect } from "react";
import { Loader2, TrendingUp, TrendingDown } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { getPriceHistory, type PriceHistoryData } from "@/lib/api";
import { getCurrencySymbol, formatPrice } from "@/lib/currency";

type Timeframe = "7D" | "1M" | "3M";

const TIMEFRAME_DAYS: Record<Timeframe, number> = {
  "7D": 7,
  "1M": 30,
  "3M": 90,
};

interface ChatPriceChartProps {
  ticker: string;
}

export default function ChatPriceChart({ ticker }: ChatPriceChartProps) {
  const [timeframe, setTimeframe] = useState<Timeframe>("1M");
  const [data, setData] = useState<PriceHistoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);

    async function fetchData() {
      const days = TIMEFRAME_DAYS[timeframe];
      // Try the ticker as-is first
      let result = await getPriceHistory(ticker, days).catch(() => null);

      // If no data and ticker has no exchange suffix, try Indian exchanges
      if ((!result?.prices?.length) && !ticker.includes(".")) {
        for (const suffix of [".NS", ".BO"]) {
          result = await getPriceHistory(`${ticker}${suffix}`, days).catch(() => null);
          if (result?.prices?.length) break;
        }
      }

      if (cancelled) return;

      if (!result?.prices?.length) {
        setError(true);
      } else {
        setData(result);
      }
    }

    fetchData()
      .catch(() => { if (!cancelled) setError(true); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => {
      cancelled = true;
    };
  }, [ticker, timeframe]);

  const currency = data?.currency ?? "USD";
  const sym = getCurrencySymbol(currency);

  const chartData =
    data?.dates.map((date, i) => ({
      date,
      price: data.prices[i],
    })) ?? [];

  const first = chartData[0]?.price ?? 0;
  const last = chartData[chartData.length - 1]?.price ?? 0;
  const change = first > 0 ? ((last - first) / first) * 100 : 0;
  const isPositive = change >= 0;
  const strokeColor = isPositive ? "#22c55e" : "#ef4444";
  const gradientId = `chat-grad-${ticker.replace(/[^a-zA-Z0-9]/g, "")}`;

  return (
    <div className="mt-3 rounded-lg border border-zinc-700/50 bg-zinc-900/40 p-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-white font-mono">{ticker}</span>
          {!loading && !error && (
            <>
              <span className="text-sm font-semibold text-white font-mono">
                {formatPrice(last, currency)}
              </span>
              <span
                className={`flex items-center gap-0.5 text-xs font-semibold ${
                  isPositive ? "text-emerald-400" : "text-red-400"
                }`}
              >
                {isPositive ? (
                  <TrendingUp className="w-3 h-3" />
                ) : (
                  <TrendingDown className="w-3 h-3" />
                )}
                {isPositive ? "+" : ""}
                {change.toFixed(2)}%
              </span>
            </>
          )}
        </div>
        <div className="flex gap-0.5 bg-zinc-800/50 rounded p-0.5">
          {(Object.keys(TIMEFRAME_DAYS) as Timeframe[]).map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-2 py-0.5 text-[10px] font-medium rounded transition-all ${
                timeframe === tf
                  ? "bg-amber-500/20 text-amber-400"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      {loading ? (
        <div className="flex items-center justify-center h-36">
          <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
        </div>
      ) : error || chartData.length === 0 ? (
        <div className="flex items-center justify-center h-36 text-zinc-500 text-xs">
          Price data not available
        </div>
      ) : (
        <div className="h-36">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 2, right: 2, bottom: 0, left: 0 }}
            >
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={strokeColor} stopOpacity={0.2} />
                  <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(63,63,70,0.2)"
              />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 9, fill: "#71717a" }}
                tickLine={false}
                axisLine={{ stroke: "rgba(63,63,70,0.2)" }}
                tickFormatter={(d) =>
                  new Date(d).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })
                }
                interval="preserveStartEnd"
                minTickGap={40}
              />
              <YAxis
                tick={{ fontSize: 9, fill: "#71717a" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${sym}${v.toFixed(0)}`}
                domain={["auto", "auto"]}
                width={45}
              />
              <Tooltip
                contentStyle={{
                  background: "rgba(9, 9, 11, 0.95)",
                  border: "1px solid rgba(63, 63, 70, 0.5)",
                  borderRadius: "6px",
                  fontSize: "11px",
                  color: "#e4e4e7",
                }}
                labelFormatter={(d) =>
                  new Date(String(d)).toLocaleDateString("en-US", {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                  })
                }
                formatter={(value) => [formatPrice(Number(value), currency), "Price"]}
              />
              <Area
                type="monotone"
                dataKey="price"
                stroke={strokeColor}
                strokeWidth={1.5}
                fill={`url(#${gradientId})`}
                dot={false}
                activeDot={{
                  r: 3,
                  fill: strokeColor,
                  stroke: "#09090b",
                  strokeWidth: 2,
                }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

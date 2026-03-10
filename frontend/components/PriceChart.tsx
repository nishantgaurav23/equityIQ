"use client";

import { useState, useEffect, useMemo } from "react";
import { Loader2, TrendingUp, TrendingDown, Minus } from "lucide-react";
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  ComposedChart, Scatter,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import { getPriceHistory, getMultiPriceHistory, getExchangeRate, type PriceHistoryData } from "@/lib/api";
import { getCurrencySymbol, formatPrice, CURRENCIES } from "@/lib/currency";

type ChartType =
  | "area"
  | "line"
  | "bar"
  | "step-line"
  | "smooth-line"
  | "stacked-area"
  | "scatter"
  | "area-bar";
type Timeframe = "7D" | "1M" | "3M" | "6M" | "1Y";

const TIMEFRAME_DAYS: Record<Timeframe, number> = {
  "7D": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365,
};

const CHART_TYPE_OPTIONS: { value: ChartType; label: string }[] = [
  { value: "area", label: "Area Chart" },
  { value: "line", label: "Line Chart" },
  { value: "smooth-line", label: "Smooth Line" },
  { value: "step-line", label: "Step Line" },
  { value: "bar", label: "Bar Chart" },
  { value: "stacked-area", label: "Stacked Area" },
  { value: "scatter", label: "Scatter Plot" },
  { value: "area-bar", label: "Area + Bar Combo" },
];

/** Infer source currency from ticker suffix when API doesn't return it */
function inferCurrency(ticker: string, apiCurrency?: string): string {
  if (apiCurrency) return apiCurrency;
  const t = ticker.toUpperCase().trim();
  if (t.endsWith(".NS") || t.endsWith(".BO")) return "INR";
  if (t.endsWith(".L")) return "GBP";
  if (t.endsWith(".TO") || t.endsWith(".V")) return "CAD";
  return "USD";
}

const STOCK_COLORS = [
  "#f59e0b", "#e11d48", "#22c55e", "#3b82f6", "#a855f7",
  "#06b6d4", "#ec4899", "#14b8a6", "#f97316", "#8b5cf6",
];

interface PriceChartProps {
  /** Single ticker or array for multi-stock overlay */
  ticker: string | string[];
  /** Show chart type selector */
  showTypeSelector?: boolean;
  /** Show currency selector */
  showCurrencySelector?: boolean;
}

interface ChartPoint {
  date: string;
  [key: string]: string | number;
}

export default function PriceChart({
  ticker,
  showTypeSelector = true,
  showCurrencySelector = true,
}: PriceChartProps) {
  const tickers = Array.isArray(ticker) ? ticker : [ticker];
  const isMulti = tickers.length > 1;

  const [chartType, setChartType] = useState<ChartType>("area");
  const [timeframe, setTimeframe] = useState<Timeframe>("3M");
  const [currency, setCurrency] = useState(() => inferCurrency(tickers[0]));
  const [rawData, setRawData] = useState<Record<string, PriceHistoryData>>({});
  const [fxRates, setFxRates] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // Fetch price data
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);

    const days = TIMEFRAME_DAYS[timeframe];
    const fetchPromise = isMulti
      ? getMultiPriceHistory(tickers, days)
      : getPriceHistory(tickers[0], days).then((d) =>
          d && d.prices ? { [tickers[0]]: d } : {}
        );

    fetchPromise
      .then((result) => {
        if (cancelled) return;
        if (!result || Object.keys(result).length === 0) {
          setRawData({});
          setError(true);
          return;
        }
        setRawData(result);
      })
      .catch(() => {
        if (!cancelled) { setRawData({}); setError(true); }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [tickers.join(","), timeframe]);

  // Fetch exchange rates per unique source currency when display currency changes
  useEffect(() => {
    // Collect unique source currencies from all tickers (infer from ticker suffix if missing)
    const sourceCurrencies = new Set<string>();
    for (const [t, d] of Object.entries(rawData)) {
      sourceCurrencies.add(inferCurrency(t, d?.currency));
    }

    const newRates: Record<string, number> = {};
    const promises: Promise<void>[] = [];

    for (const src of sourceCurrencies) {
      if (src === currency) {
        newRates[src] = 1;
      } else {
        promises.push(
          getExchangeRate(src, currency)
            .then((r) => { newRates[src] = r.rate; })
            .catch(() => { newRates[src] = 1; })
        );
      }
    }

    if (promises.length === 0) {
      setFxRates(newRates);
    } else {
      Promise.all(promises).then(() => setFxRates(newRates));
    }
  }, [currency, rawData]);

  // Merge data for chart — apply per-ticker FX rates
  const { chartData, summaries } = useMemo(() => {
    const dataMap: Record<string, Record<string, number>> = {};
    const sums: Record<string, { first: number; last: number; currency: string }> = {};

    for (const [t, d] of Object.entries(rawData)) {
      if (!d?.prices?.length) continue;
      const srcCurrency = inferCurrency(t, d.currency);
      const rate = fxRates[srcCurrency] ?? 1;
      sums[t] = {
        first: d.prices[0] * rate,
        last: d.prices[d.prices.length - 1] * rate,
        currency: srcCurrency,
      };
      d.dates.forEach((date, i) => {
        if (!dataMap[date]) dataMap[date] = {};
        dataMap[date][t] = d.prices[i] * rate;
      });
    }

    const sorted = Object.entries(dataMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, vals]) => ({ date, ...vals } as ChartPoint));

    return { chartData: sorted, summaries: sums };
  }, [rawData, fxRates, currency]);

  const sym = getCurrencySymbol(currency);

  const formatXTick = (d: string) => {
    const date = new Date(d);
    return timeframe === "7D" || timeframe === "1M"
      ? date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
      : date.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
  };

  const formatYTick = (v: number) => `${sym}${v.toFixed(0)}`;

  const tooltipStyle = {
    background: "rgba(9, 9, 11, 0.95)",
    border: "1px solid rgba(63, 63, 70, 0.5)",
    borderRadius: "8px",
    fontSize: "12px",
    color: "#e4e4e7",
  };

  const renderChart = () => {
    const commonProps = {
      data: chartData,
      margin: { top: 4, right: 4, bottom: 0, left: 0 },
    };

    const axes = (
      <>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(63,63,70,0.25)" />
        <XAxis
          dataKey="date" tick={{ fontSize: 10, fill: "#71717a" }}
          tickLine={false} axisLine={{ stroke: "rgba(63,63,70,0.25)" }}
          tickFormatter={formatXTick} interval="preserveStartEnd" minTickGap={40}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#71717a" }} tickLine={false} axisLine={false}
          tickFormatter={formatYTick} domain={["auto", "auto"]} width={55}
        />
        <Tooltip
          contentStyle={tooltipStyle}
          labelFormatter={(d) => new Date(String(d)).toLocaleDateString("en-US", {
            weekday: "short", month: "short", day: "numeric", year: "numeric",
          })}
          formatter={(value, name) => [
            formatPrice(Number(value), currency), String(name),
          ]}
        />
        {isMulti && <Legend wrapperStyle={{ fontSize: "11px", color: "#a1a1aa" }} />}
      </>
    );

    // Line chart (straight segments)
    if (chartType === "line") {
      return (
        <LineChart {...commonProps}>
          {axes}
          {tickers.map((t, i) => (
            <Line
              key={t} type="linear" dataKey={t}
              stroke={STOCK_COLORS[i % STOCK_COLORS.length]}
              strokeWidth={2} dot={false}
              activeDot={{ r: 4, stroke: "#09090b", strokeWidth: 2 }}
            />
          ))}
        </LineChart>
      );
    }

    // Smooth line (monotone curve)
    if (chartType === "smooth-line") {
      return (
        <LineChart {...commonProps}>
          {axes}
          {tickers.map((t, i) => (
            <Line
              key={t} type="monotone" dataKey={t}
              stroke={STOCK_COLORS[i % STOCK_COLORS.length]}
              strokeWidth={2} dot={false}
              activeDot={{ r: 4, stroke: "#09090b", strokeWidth: 2 }}
            />
          ))}
        </LineChart>
      );
    }

    // Step line
    if (chartType === "step-line") {
      return (
        <LineChart {...commonProps}>
          {axes}
          {tickers.map((t, i) => (
            <Line
              key={t} type="stepAfter" dataKey={t}
              stroke={STOCK_COLORS[i % STOCK_COLORS.length]}
              strokeWidth={2} dot={false}
              activeDot={{ r: 4, stroke: "#09090b", strokeWidth: 2 }}
            />
          ))}
        </LineChart>
      );
    }

    // Bar chart
    if (chartType === "bar") {
      return (
        <BarChart {...commonProps}>
          {axes}
          {tickers.map((t, i) => (
            <Bar
              key={t} dataKey={t}
              fill={STOCK_COLORS[i % STOCK_COLORS.length]}
              opacity={0.8} radius={[2, 2, 0, 0]}
            />
          ))}
        </BarChart>
      );
    }

    // Stacked area
    if (chartType === "stacked-area") {
      return (
        <AreaChart {...commonProps}>
          <defs>
            {tickers.map((t, i) => (
              <linearGradient key={t} id={`grad-stack-${t}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={STOCK_COLORS[i % STOCK_COLORS.length]} stopOpacity={0.4} />
                <stop offset="100%" stopColor={STOCK_COLORS[i % STOCK_COLORS.length]} stopOpacity={0.05} />
              </linearGradient>
            ))}
          </defs>
          {axes}
          {tickers.map((t, i) => (
            <Area
              key={t} type="monotone" dataKey={t}
              stroke={STOCK_COLORS[i % STOCK_COLORS.length]}
              strokeWidth={1.5} fill={`url(#grad-stack-${t})`}
              stackId="1" dot={false}
              activeDot={{ r: 3, fill: STOCK_COLORS[i % STOCK_COLORS.length], stroke: "#09090b", strokeWidth: 2 }}
            />
          ))}
        </AreaChart>
      );
    }

    // Scatter plot
    if (chartType === "scatter") {
      return (
        <ComposedChart {...commonProps}>
          {axes}
          {tickers.map((t, i) => (
            <Scatter
              key={t} dataKey={t} name={t}
              fill={STOCK_COLORS[i % STOCK_COLORS.length]}
              opacity={0.7}
            />
          ))}
        </ComposedChart>
      );
    }

    // Area + Bar combo (first ticker as area, rest as bars)
    if (chartType === "area-bar") {
      return (
        <ComposedChart {...commonProps}>
          <defs>
            <linearGradient id="grad-combo-0" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={STOCK_COLORS[0]} stopOpacity={0.2} />
              <stop offset="100%" stopColor={STOCK_COLORS[0]} stopOpacity={0} />
            </linearGradient>
          </defs>
          {axes}
          {tickers.map((t, i) =>
            i === 0 ? (
              <Area
                key={t} type="monotone" dataKey={t}
                stroke={STOCK_COLORS[0]} strokeWidth={2}
                fill="url(#grad-combo-0)" dot={false}
                activeDot={{ r: 4, fill: STOCK_COLORS[0], stroke: "#09090b", strokeWidth: 2 }}
              />
            ) : (
              <Bar
                key={t} dataKey={t}
                fill={STOCK_COLORS[i % STOCK_COLORS.length]}
                opacity={0.6} radius={[2, 2, 0, 0]}
              />
            )
          )}
        </ComposedChart>
      );
    }

    // Default: area
    return (
      <AreaChart {...commonProps}>
        <defs>
          {tickers.map((t, i) => (
            <linearGradient key={t} id={`grad-${t}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={STOCK_COLORS[i % STOCK_COLORS.length]} stopOpacity={0.2} />
              <stop offset="100%" stopColor={STOCK_COLORS[i % STOCK_COLORS.length]} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        {axes}
        {tickers.map((t, i) => (
          <Area
            key={t} type="monotone" dataKey={t}
            stroke={STOCK_COLORS[i % STOCK_COLORS.length]}
            strokeWidth={2} fill={`url(#grad-${t})`} dot={false}
            activeDot={{ r: 4, fill: STOCK_COLORS[i % STOCK_COLORS.length], stroke: "#09090b", strokeWidth: 2 }}
          />
        ))}
      </AreaChart>
    );
  };

  return (
    <div className="glass rounded-xl p-5 space-y-4">
      {/* Header Row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
            Price History
          </h3>
          {/* Single stock price summary */}
          {!isMulti && Object.keys(summaries).length > 0 && (() => {
            const s = Object.values(summaries)[0];
            const change = s.last - s.first;
            const pct = s.first > 0 ? (change / s.first) * 100 : 0;
            const pos = change >= 0;
            return (
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold text-white font-mono">
                  {formatPrice(s.last, currency)}
                </span>
                <span className={`flex items-center gap-0.5 text-sm font-semibold ${pos ? "text-green-400" : "text-red-400"}`}>
                  {pos ? <TrendingUp className="w-3.5 h-3.5" /> : change === 0 ? <Minus className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                  {pos ? "+" : ""}{pct.toFixed(2)}%
                </span>
              </div>
            );
          })()}
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Chart Type Dropdown */}
          {showTypeSelector && (
            <select
              value={chartType}
              onChange={(e) => setChartType(e.target.value as ChartType)}
              className="bg-zinc-900/50 border border-zinc-800 rounded-lg px-2 py-1 text-[11px] text-zinc-400 focus:outline-none focus:border-amber-500/30"
            >
              {CHART_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          )}

          {/* Currency Selector */}
          {showCurrencySelector && (
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="bg-zinc-900/50 border border-zinc-800 rounded-lg px-2 py-1 text-[11px] text-zinc-400 focus:outline-none focus:border-amber-500/30"
            >
              {CURRENCIES.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.symbol} {c.code}
                </option>
              ))}
            </select>
          )}

          {/* Timeframe Tabs */}
          <div className="flex gap-0.5 bg-zinc-900/50 rounded-lg p-0.5">
            {(Object.keys(TIMEFRAME_DAYS) as Timeframe[]).map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${
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
      </div>

      {/* Multi-stock summary badges */}
      {isMulti && Object.keys(summaries).length > 0 && (
        <div className="flex flex-wrap gap-3">
          {Object.entries(summaries).map(([t, s], i) => {
            const change = s.last - s.first;
            const pct = s.first > 0 ? (change / s.first) * 100 : 0;
            const pos = change >= 0;
            return (
              <div key={t} className="glass-dark rounded-lg px-3 py-2 flex items-center gap-2">
                <div
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ background: STOCK_COLORS[i % STOCK_COLORS.length] }}
                />
                <span className="font-mono text-sm font-semibold text-white">{t}</span>
                <span className="text-sm text-zinc-400">{formatPrice(s.last, currency)}</span>
                <span className={`text-xs font-semibold ${pos ? "text-green-400" : "text-red-400"}`}>
                  {pos ? "+" : ""}{pct.toFixed(1)}%
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Chart */}
      {loading ? (
        <div className="flex items-center justify-center h-56">
          <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />
        </div>
      ) : error || chartData.length === 0 ? (
        <div className="flex items-center justify-center h-56 text-zinc-500 text-sm">
          Price data not available for this timeframe.
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            {renderChart()}
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

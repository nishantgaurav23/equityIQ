"use client";

import type { SignalSnapshot, FinalSignal } from "@/types/api";

interface SignalTrendChartProps {
  snapshots: SignalSnapshot[];
}

const SIGNAL_LEVEL: Record<FinalSignal, number> = {
  STRONG_BUY: 2,
  BUY: 1,
  HOLD: 0,
  SELL: -1,
  STRONG_SELL: -2,
};

const SIGNAL_COLOR: Record<FinalSignal, string> = {
  STRONG_BUY: "#059669",
  BUY: "#22c55e",
  HOLD: "#f59e0b",
  SELL: "#ef4444",
  STRONG_SELL: "#be123c",
};

const Y_LABELS = [
  { level: 2, label: "STRONG_BUY" },
  { level: 1, label: "BUY" },
  { level: 0, label: "HOLD" },
  { level: -1, label: "SELL" },
  { level: -2, label: "STRONG_SELL" },
];

export default function SignalTrendChart({ snapshots }: SignalTrendChartProps) {
  if (snapshots.length === 0) {
    return (
      <p className="text-gray-500 dark:text-gray-400 text-center py-8">
        No trend data available.
      </p>
    );
  }

  const width = 600;
  const height = 240;
  const padding = { top: 20, right: 20, bottom: 40, left: 100 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const xScale = (i: number) =>
    padding.left + (snapshots.length === 1 ? chartW / 2 : (i / (snapshots.length - 1)) * chartW);
  const yScale = (level: number) =>
    padding.top + ((2 - level) / 4) * chartH;

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full max-w-2xl mx-auto">
        {/* Y-axis labels */}
        {Y_LABELS.map(({ level, label }) => (
          <g key={label}>
            <line
              x1={padding.left}
              x2={width - padding.right}
              y1={yScale(level)}
              y2={yScale(level)}
              stroke="#e5e7eb"
              strokeDasharray="4 2"
            />
            <text
              x={padding.left - 8}
              y={yScale(level) + 4}
              textAnchor="end"
              className="text-[10px] fill-gray-400"
            >
              {label}
            </text>
          </g>
        ))}

        {/* Line connecting points */}
        {snapshots.length > 1 && (
          <polyline
            points={snapshots
              .map((s, i) => `${xScale(i)},${yScale(SIGNAL_LEVEL[s.final_signal])}`)
              .join(" ")}
            fill="none"
            stroke="#6b7280"
            strokeWidth={1.5}
          />
        )}

        {/* Data points */}
        {snapshots.map((s, i) => {
          const cx = xScale(i);
          const cy = yScale(SIGNAL_LEVEL[s.final_signal]);
          const r = 4 + s.overall_confidence * 4;
          return (
            <g key={s.session_id}>
              <circle
                cx={cx}
                cy={cy}
                r={r}
                fill={SIGNAL_COLOR[s.final_signal]}
                opacity={0.5 + s.overall_confidence * 0.5}
              />
              <text
                x={cx}
                y={height - 8}
                textAnchor="middle"
                className="text-[9px] fill-gray-400"
              >
                {new Date(s.created_at).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                })}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

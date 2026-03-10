"use client";

import type { FinalVerdict, FinalSignal } from "@/types/api";

interface HistoryTableProps {
  verdicts: FinalVerdict[];
}

function signalBadgeClass(signal: FinalSignal): string {
  switch (signal) {
    case "STRONG_BUY":
      return "bg-emerald-600 text-white";
    case "BUY":
      return "bg-green-500 text-white";
    case "HOLD":
      return "bg-amber-400 text-gray-900";
    case "SELL":
      return "bg-red-500 text-white";
    case "STRONG_SELL":
      return "bg-rose-700 text-white";
    default:
      return "bg-gray-400 text-white";
  }
}

export default function HistoryTable({ verdicts }: HistoryTableProps) {
  if (verdicts.length === 0) {
    return (
      <p className="text-gray-500 dark:text-gray-400 text-center py-8">
        No analyses found for this ticker.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700 text-left">
            <th className="py-3 px-2 font-medium">Date</th>
            <th className="py-3 px-2 font-medium">Signal</th>
            <th className="py-3 px-2 font-medium">Confidence</th>
            <th className="py-3 px-2 font-medium">Key Drivers</th>
            <th className="py-3 px-2 font-medium">Session</th>
          </tr>
        </thead>
        <tbody>
          {verdicts.map((v) => (
            <tr
              key={v.session_id}
              className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900"
            >
              <td className="py-2 px-2 whitespace-nowrap">
                {new Date(v.timestamp).toLocaleDateString()}
              </td>
              <td className="py-2 px-2">
                <span
                  className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${signalBadgeClass(v.final_signal)}`}
                >
                  {v.final_signal}
                </span>
              </td>
              <td className="py-2 px-2">
                {(v.overall_confidence * 100).toFixed(0)}%
              </td>
              <td className="py-2 px-2 max-w-xs truncate">
                {v.key_drivers.slice(0, 2).join(", ")}
              </td>
              <td className="py-2 px-2 font-mono text-xs text-gray-400">
                {v.session_id.slice(0, 8)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

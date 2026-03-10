"use client";

import { motion } from "framer-motion";
import { FileText, Trophy, AlertTriangle, TrendingUp, Shield } from "lucide-react";
import type { FinalVerdict } from "@/types/api";
import SignalBadge from "@/components/SignalBadge";

interface ComparisonReportProps {
  verdicts: FinalVerdict[];
}

const SIGNAL_SCORE: Record<string, number> = {
  STRONG_BUY: 5,
  BUY: 4,
  HOLD: 3,
  SELL: 2,
  STRONG_SELL: 1,
};

export default function ComparisonReport({ verdicts }: ComparisonReportProps) {
  if (verdicts.length < 2) return null;

  // Rank stocks
  const ranked = [...verdicts].sort((a, b) => {
    const sa = SIGNAL_SCORE[a.final_signal] ?? 3;
    const sb = SIGNAL_SCORE[b.final_signal] ?? 3;
    if (sa !== sb) return sb - sa;
    return b.overall_confidence - a.overall_confidence;
  });

  const topPick = ranked[0];
  const bottomPick = ranked[ranked.length - 1];

  // Calculate averages
  const avgConfidence =
    verdicts.reduce((sum, v) => sum + v.overall_confidence, 0) / verdicts.length;
  const buyCount = verdicts.filter(
    (v) => v.final_signal === "BUY" || v.final_signal === "STRONG_BUY"
  ).length;
  const sellCount = verdicts.filter(
    (v) => v.final_signal === "SELL" || v.final_signal === "STRONG_SELL"
  ).length;
  const holdCount = verdicts.filter((v) => v.final_signal === "HOLD").length;

  const highRiskCount = verdicts.filter((v) => v.risk_level === "HIGH").length;
  const lowRiskCount = verdicts.filter((v) => v.risk_level === "LOW").length;

  // Build recommendation
  let overallRecommendation: string;
  let recommendationColor: string;
  if (buyCount > sellCount && buyCount > holdCount) {
    overallRecommendation = "Overall Bullish";
    recommendationColor = "text-green-400";
  } else if (sellCount > buyCount && sellCount > holdCount) {
    overallRecommendation = "Overall Bearish";
    recommendationColor = "text-red-400";
  } else {
    overallRecommendation = "Mixed Signals";
    recommendationColor = "text-amber-400";
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-2xl p-6 space-y-6"
    >
      {/* Report Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-rose-600 flex items-center justify-center">
          <FileText className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-white">Combined Assessment</h3>
          <p className="text-xs text-zinc-500">
            AI analysis of {verdicts.length} stocks compared
          </p>
        </div>
        <span className={`ml-auto text-lg font-bold ${recommendationColor}`}>
          {overallRecommendation}
        </span>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="glass-dark rounded-lg p-3">
          <p className="text-[10px] text-zinc-500 uppercase">Stocks</p>
          <p className="text-xl font-bold text-white">{verdicts.length}</p>
        </div>
        <div className="glass-dark rounded-lg p-3">
          <p className="text-[10px] text-zinc-500 uppercase">Buy Signals</p>
          <p className="text-xl font-bold text-green-400">{buyCount}</p>
        </div>
        <div className="glass-dark rounded-lg p-3">
          <p className="text-[10px] text-zinc-500 uppercase">Hold Signals</p>
          <p className="text-xl font-bold text-amber-400">{holdCount}</p>
        </div>
        <div className="glass-dark rounded-lg p-3">
          <p className="text-[10px] text-zinc-500 uppercase">Sell Signals</p>
          <p className="text-xl font-bold text-red-400">{sellCount}</p>
        </div>
        <div className="glass-dark rounded-lg p-3">
          <p className="text-[10px] text-zinc-500 uppercase">Avg Confidence</p>
          <p className="text-xl font-bold text-amber-400 font-mono">
            {Math.round(avgConfidence * 100)}%
          </p>
        </div>
      </div>

      {/* Rankings Table */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
          Stock Rankings (Best to Worst)
        </h4>
        <div className="space-y-2">
          {ranked.map((v, i) => (
            <div
              key={v.ticker}
              className={`glass-dark rounded-lg p-3 flex items-center justify-between ${
                i === 0 ? "border border-amber-500/20" : ""
              }`}
            >
              <div className="flex items-center gap-3">
                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  i === 0
                    ? "bg-amber-500/20 text-amber-400"
                    : "bg-zinc-800 text-zinc-500"
                }`}>
                  {i + 1}
                </span>
                <span className="font-mono font-bold text-white text-sm">{v.ticker}</span>
                <SignalBadge signal={v.final_signal} size="sm" />
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-zinc-400 font-mono">
                  {Math.round(v.overall_confidence * 100)}%
                </span>
                <span className={`text-xs font-semibold ${
                  v.risk_level === "LOW" ? "text-green-400" :
                  v.risk_level === "HIGH" ? "text-red-400" : "text-amber-400"
                }`}>
                  {v.risk_level === "LOW" ? "Low Risk" : v.risk_level === "HIGH" ? "High Risk" : "Med Risk"}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Key Insights */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Top Pick */}
        <div className="rounded-xl bg-green-500/5 border border-green-500/15 p-4 space-y-2">
          <div className="flex items-center gap-2">
            <Trophy className="w-4 h-4 text-amber-400" />
            <span className="text-xs font-semibold text-zinc-400 uppercase">Top Pick</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xl font-bold text-white">{topPick.ticker}</span>
            <SignalBadge signal={topPick.final_signal} size="sm" />
          </div>
          <p className="text-xs text-zinc-400">
            Highest conviction at {Math.round(topPick.overall_confidence * 100)}% confidence
            with {topPick.risk_level?.toLowerCase() ?? "moderate"} risk.
          </p>
          {topPick.key_drivers[0] && (
            <p className="text-xs text-zinc-500 italic">
              &ldquo;{topPick.key_drivers.find((d) => !d.startsWith("WARNING:")) ?? topPick.key_drivers[0]}&rdquo;
            </p>
          )}
        </div>

        {/* Risk Alert */}
        <div className="rounded-xl bg-zinc-500/5 border border-zinc-500/15 p-4 space-y-2">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-amber-400" />
            <span className="text-xs font-semibold text-zinc-400 uppercase">Risk Overview</span>
          </div>
          <div className="space-y-1.5">
            {highRiskCount > 0 && (
              <p className="text-sm text-red-400 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" />
                {highRiskCount} stock{highRiskCount > 1 ? "s" : ""} flagged high risk
              </p>
            )}
            {lowRiskCount > 0 && (
              <p className="text-sm text-green-400 flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5" />
                {lowRiskCount} stock{lowRiskCount > 1 ? "s" : ""} at low risk
              </p>
            )}
            {highRiskCount === 0 && lowRiskCount === 0 && (
              <p className="text-sm text-amber-400">
                All stocks show moderate risk levels.
              </p>
            )}
          </div>
          <p className="text-xs text-zinc-500">
            Consider diversifying across different risk levels for a balanced portfolio.
          </p>
        </div>
      </div>

      {/* Final Recommendation */}
      <div className="rounded-xl bg-amber-500/5 border border-amber-500/15 p-4 space-y-2">
        <h4 className="text-xs font-semibold text-zinc-400 uppercase">Final Recommendation</h4>
        <p className="text-sm text-zinc-300 leading-relaxed">
          {buyCount > sellCount ? (
            <>
              Based on AI analysis, <strong className="text-green-400">{topPick.ticker}</strong> is
              the strongest candidate with a {topPick.final_signal.replace("_", " ")} signal
              at {Math.round(topPick.overall_confidence * 100)}% confidence.
              {highRiskCount > 0 && (
                <> Be cautious with {ranked.filter((v) => v.risk_level === "HIGH").map((v) => v.ticker).join(", ")} due to high risk.</>
              )}
            </>
          ) : sellCount > buyCount ? (
            <>
              The overall outlook is bearish. {sellCount} out of {verdicts.length} stocks received
              sell signals. Consider reducing exposure, especially in{" "}
              <strong className="text-red-400">{bottomPick.ticker}</strong>.
            </>
          ) : (
            <>
              Mixed signals across the board. {topPick.ticker} shows the most promise,
              while the rest are in hold territory. Consider waiting for clearer trends
              before making significant moves.
            </>
          )}
        </p>
      </div>
    </motion.div>
  );
}

"use client";

import { motion } from "framer-motion";
import { FileText, TrendingUp, TrendingDown, Minus, ShieldAlert, Info } from "lucide-react";
import type { FinalVerdict, AgentDetail } from "@/types/api";
import { getAgentMeta } from "@/lib/agents";
import { humanizeText } from "@/lib/metric-labels";
import SignalBadge from "@/components/SignalBadge";

interface StockReportProps {
  verdict: FinalVerdict;
}

const SIGNAL_LABEL: Record<string, string> = {
  STRONG_BUY: "Strong Buy",
  BUY: "Buy",
  HOLD: "Hold",
  SELL: "Sell",
  STRONG_SELL: "Strong Sell",
};

const SIGNAL_ADVICE: Record<string, string> = {
  STRONG_BUY:
    "Our AI agents show strong consensus that this stock is significantly undervalued with positive momentum. Consider building a position, keeping in mind the suggested position size from the Risk Guardian.",
  BUY:
    "Multiple agents indicate favorable conditions for this stock. The combination of fundamentals, momentum, and market conditions suggests potential upside. Consider adding to your portfolio with appropriate position sizing.",
  HOLD:
    "The signals are mixed across our agents. While there's no strong case to sell, it's also not the optimal time to add more. Hold your current position and monitor for changes in the key drivers below.",
  SELL:
    "Several agents flag concerns with this stock. Whether it's deteriorating fundamentals, negative momentum, or elevated risk, the weight of evidence suggests reducing your position.",
  STRONG_SELL:
    "Our agents show strong consensus against this stock. Multiple red flags have been identified across fundamentals, momentum, and/or regulatory concerns. Consider exiting this position to protect capital.",
};

function getAgentExplanation(agentName: string, detail: AgentDetail): string {
  const meta = getAgentMeta(agentName);
  const signal = detail.signal;
  const conf = Math.round(detail.confidence * 100);

  const signalWord = signal === "BUY" || signal === "STRONG_BUY"
    ? "positive"
    : signal === "SELL" || signal === "STRONG_SELL"
      ? "negative"
      : "neutral";

  if (detail.reasoning) {
    return detail.reasoning;
  }

  return `${meta.displayName} found ${signalWord} signals at ${conf}% confidence.`;
}

export default function StockReport({ verdict }: StockReportProps) {
  const signalLabel = SIGNAL_LABEL[verdict.final_signal] ?? verdict.final_signal;
  const advice = SIGNAL_ADVICE[verdict.final_signal] ?? "";
  const confPct = Math.round(verdict.overall_confidence * 100);

  const isBullish = verdict.final_signal === "BUY" || verdict.final_signal === "STRONG_BUY";
  const isBearish = verdict.final_signal === "SELL" || verdict.final_signal === "STRONG_SELL";

  const SignalIcon = isBullish ? TrendingUp : isBearish ? TrendingDown : Minus;
  const signalColor = isBullish ? "text-green-400" : isBearish ? "text-red-400" : "text-amber-400";
  const borderColor = isBullish
    ? "border-green-500/20"
    : isBearish
      ? "border-red-500/20"
      : "border-amber-500/20";

  // Sort agents: directional first (not RiskGuardian), then RiskGuardian last
  const agentEntries = Object.entries(verdict.analyst_details || {}).sort(([a], [b]) => {
    if (a === "RiskGuardian") return 1;
    if (b === "RiskGuardian") return -1;
    return 0;
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className={`glass rounded-2xl p-6 space-y-6 border ${borderColor}`}
    >
      {/* Report Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-rose-600 flex items-center justify-center">
          <FileText className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-bold text-white">
            Analysis Report: {verdict.ticker}
          </h3>
          <p className="text-xs text-zinc-500">
            AI-powered analysis from 7 specialist agents
          </p>
        </div>
        <div className="flex items-center gap-2">
          <SignalIcon className={`w-5 h-5 ${signalColor}`} />
          <span className={`text-xl font-bold ${signalColor}`}>{signalLabel}</span>
        </div>
      </div>

      {/* Main Verdict Box */}
      <div className={`rounded-xl p-4 space-y-3 ${
        isBullish ? "bg-green-500/5 border border-green-500/15" :
        isBearish ? "bg-red-500/5 border border-red-500/15" :
        "bg-amber-500/5 border border-amber-500/15"
      }`}>
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            Final Verdict
          </span>
          <span className={`text-sm font-bold ${signalColor}`}>
            {confPct}% Confidence
          </span>
        </div>
        <p className="text-sm text-zinc-300 leading-relaxed">
          {advice}
        </p>
      </div>

      {/* Agent-by-Agent Breakdown */}
      <div className="space-y-3">
        <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
          <Info className="w-3.5 h-3.5 text-amber-400" />
          What Each Agent Found
        </h4>
        <div className="space-y-2">
          {agentEntries.map(([name, detail]) => {
            const meta = getAgentMeta(name);
            const agentSignal = detail.signal;
            const agentConf = Math.round(detail.confidence * 100);
            const isAgentBullish = agentSignal === "BUY" || agentSignal === "STRONG_BUY";
            const isAgentBearish = agentSignal === "SELL" || agentSignal === "STRONG_SELL";
            const agentColor = isAgentBullish
              ? "text-green-400"
              : isAgentBearish
                ? "text-red-400"
                : "text-amber-400";

            return (
              <div
                key={name}
                className="glass-dark rounded-lg p-3 space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white">
                      {meta.displayName}
                    </span>
                    <span className="text-[10px] text-zinc-600">{meta.role}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-bold ${agentColor}`}>
                      {SIGNAL_LABEL[agentSignal] ?? agentSignal}
                    </span>
                    <span className="text-[10px] text-zinc-500 font-mono">{agentConf}%</span>
                  </div>
                </div>
                <p className="text-xs text-zinc-400 leading-relaxed">
                  {humanizeText(getAgentExplanation(name, detail))}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Key Drivers */}
      {verdict.key_drivers.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            Key Drivers
          </h4>
          <ul className="space-y-1.5">
            {verdict.key_drivers
              .filter((d) => !d.startsWith("WARNING:"))
              .map((driver, i) => (
                <li key={i} className="text-sm text-zinc-300 flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">&#8226;</span>
                  {driver}
                </li>
              ))}
          </ul>
          {verdict.key_drivers.filter((d) => d.startsWith("WARNING:")).length > 0 && (
            <div className="mt-2 rounded-lg bg-yellow-500/5 border border-yellow-500/15 p-3 space-y-1">
              <div className="flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5 text-yellow-500" />
                <span className="text-xs font-semibold text-yellow-500">Warnings</span>
              </div>
              {verdict.key_drivers
                .filter((d) => d.startsWith("WARNING:"))
                .map((w, i) => (
                  <p key={i} className="text-xs text-yellow-400/70">
                    {w.replace("WARNING:", "").trim()}
                  </p>
                ))}
            </div>
          )}
        </div>
      )}

      {/* Risk Summary */}
      {verdict.risk_summary && (
        <div className="rounded-lg bg-zinc-500/5 border border-zinc-500/15 p-3 space-y-1">
          <span className="text-xs font-semibold text-zinc-400 uppercase">Risk Summary</span>
          <p className="text-xs text-zinc-400 leading-relaxed">{verdict.risk_summary}</p>
        </div>
      )}
    </motion.div>
  );
}

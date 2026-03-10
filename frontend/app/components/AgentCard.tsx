"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart3, TrendingUp, Newspaper, Globe, ShieldCheck, ShieldAlert,
  HelpCircle, CheckCircle2, ChevronDown, ChevronUp, Info,
} from "lucide-react";
import { getAgentMeta } from "@/lib/agents";
import { getMetricLabel, getMetricTooltip, formatMetricValue, humanizeText } from "@/lib/metric-labels";
import type { AgentDetail } from "@/types/api";

const ICON_MAP: Record<string, React.ElementType> = {
  BarChart3, TrendingUp, Newspaper, Globe, ShieldCheck, ShieldAlert, HelpCircle,
};

interface AgentCardProps {
  agentName: string;
  signal: string;
  detail?: AgentDetail;
  index?: number;
  ticker?: string;
}

const signalLabels: Record<string, string> = {
  BUY: "Buy", STRONG_BUY: "Strong Buy", HOLD: "Hold",
  SELL: "Sell", STRONG_SELL: "Strong Sell",
};

const signalColor: Record<string, string> = {
  BUY: "text-green-400", STRONG_BUY: "text-green-400",
  HOLD: "text-amber-400",
  SELL: "text-red-400", STRONG_SELL: "text-red-400",
};

export default function AgentCard({ agentName, signal, detail, index = 0, ticker }: AgentCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [hoveredMetric, setHoveredMetric] = useState<string | null>(null);
  const meta = getAgentMeta(agentName);
  const IconComp = ICON_MAP[meta.icon] ?? HelpCircle;
  const confidence = detail?.confidence ?? 0;
  const pct = Math.round(confidence * 100);

  const barColor =
    confidence > 0.6
      ? "from-green-500 to-emerald-400"
      : confidence > 0.3
        ? "from-amber-500 to-yellow-400"
        : "from-red-500 to-rose-400";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className="glass rounded-xl p-4 space-y-3 transition-default"
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${meta.color} flex items-center justify-center`}>
            <IconComp className="w-4.5 h-4.5 text-white" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white">{meta.displayName}</h4>
            <p className="text-xs text-zinc-500">{meta.role}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {detail && <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />}
          <span className={`text-xs font-bold ${signalColor[signal] ?? "text-zinc-400"}`}>
            {signalLabels[signal] ?? signal}
          </span>
        </div>
      </div>

      {/* Confidence Bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs">
          <span className="text-zinc-500">Confidence</span>
          <span className="font-mono text-white">{pct}%</span>
        </div>
        <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ delay: index * 0.08 + 0.3, duration: 0.6, ease: "easeOut" }}
            className={`h-full rounded-full bg-gradient-to-r ${barColor}`}
          />
        </div>
      </div>

      {/* Data Source Badge */}
      {detail?.data_source && (
        <div className="flex items-center gap-2">
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
            {detail.data_source}
          </span>
          {detail.execution_time_ms > 0 && (
            <span className="text-[10px] text-zinc-500">
              {(detail.execution_time_ms / 1000).toFixed(1)}s
            </span>
          )}
        </div>
      )}

      {/* Key Metrics */}
      {detail && Object.keys(detail.key_metrics).length > 0 && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
          {Object.entries(detail.key_metrics)
            .filter(([, v]) => v != null && v !== "" && !Array.isArray(v))
            .slice(0, expanded ? undefined : 4)
            .map(([key, value]) => (
              <div
                key={key}
                className="relative group"
                onMouseEnter={() => setHoveredMetric(key)}
                onMouseLeave={() => setHoveredMetric(null)}
              >
                <div className="flex justify-between text-[11px]">
                  <span className="text-zinc-500 truncate flex items-center gap-0.5">
                    {getMetricLabel(key, ticker)}
                    {getMetricTooltip(key, ticker) && (
                      <Info className="w-2.5 h-2.5 text-zinc-600" />
                    )}
                  </span>
                  <span className="font-mono text-zinc-300 ml-1">
                    {formatMetricValue(key, value)}
                  </span>
                </div>
                {hoveredMetric === key && getMetricTooltip(key, ticker) && (
                  <div className="absolute z-50 bottom-full left-0 mb-1 w-56 p-2 rounded-lg bg-zinc-900/95 border border-zinc-700/50 text-[10px] text-zinc-400 leading-relaxed shadow-lg">
                    {getMetricTooltip(key, ticker)}
                  </div>
                )}
              </div>
            ))}
        </div>
      )}

      {/* Reasoning (expandable) */}
      {detail?.reasoning && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full text-left"
        >
          <div className="text-xs text-zinc-400 leading-relaxed">
            {expanded ? humanizeText(detail.reasoning) : humanizeText(detail.reasoning.slice(0, 100))}
            {detail.reasoning.length > 100 && !expanded && "..."}
          </div>
          {(detail.reasoning.length > 100 || Object.keys(detail.key_metrics).length > 4) && (
            <div className="flex items-center gap-1 mt-1 text-[10px] text-amber-400">
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {expanded ? "Show Less" : "Show More"}
            </div>
          )}
        </button>
      )}
    </motion.div>
  );
}

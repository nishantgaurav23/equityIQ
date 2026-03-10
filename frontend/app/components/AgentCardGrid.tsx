"use client";

import AgentCard from "./AgentCard";
import type { AgentDetail } from "@/types/api";

interface AgentCardGridProps {
  signals: Record<string, string>;
  details?: Record<string, AgentDetail>;
  ticker?: string;
}

export default function AgentCardGrid({ signals, details, ticker }: AgentCardGridProps) {
  const entries = Object.entries(signals);

  if (entries.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
        Agent Signals
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {entries.map(([agent, signal], i) => (
          <AgentCard
            key={agent}
            agentName={agent}
            signal={signal}
            detail={details?.[agent]}
            index={i}
            ticker={ticker}
          />
        ))}
      </div>
    </div>
  );
}

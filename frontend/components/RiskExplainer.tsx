"use client";

import { useState } from "react";
import { Info, ChevronDown, ChevronUp, ShieldAlert } from "lucide-react";

interface RiskExplainerProps {
  riskLevel: string;
  riskSummary: string;
  analystDetails?: Record<string, { key_metrics: Record<string, unknown> }>;
}

interface RiskInsight {
  label: string;
  value: string;
  explanation: string;
  color: string;
}

function parseRiskMetrics(
  riskSummary: string,
  details?: Record<string, { key_metrics: Record<string, unknown> }>,
): RiskInsight[] {
  const insights: RiskInsight[] = [];
  const riskMetrics = details?.RiskGuardian?.key_metrics ?? {};

  const beta = riskMetrics.beta as number | undefined;
  if (beta != null) {
    let explanation: string;
    let color: string;
    if (Math.abs(beta) < 0.5) {
      explanation = "This stock barely follows the market — it moves independently.";
      color = "text-green-400";
    } else if (beta < 0) {
      explanation = "This stock tends to move opposite to the market.";
      color = "text-amber-400";
    } else if (beta <= 1.2) {
      explanation = "This stock moves roughly in line with the overall market — moderate and predictable.";
      color = "text-green-400";
    } else {
      explanation = "This stock swings more than the market. Bigger potential gains, but also bigger losses.";
      color = "text-red-400";
    }
    insights.push({ label: "Market Sensitivity", value: beta.toFixed(2), explanation, color });
  }

  const vol = riskMetrics.annualized_volatility as number | undefined;
  if (vol != null) {
    let explanation: string;
    let color: string;
    if (vol < 0.2) {
      explanation = "Relatively calm stock. Price changes are small and steady day-to-day.";
      color = "text-green-400";
    } else if (vol < 0.4) {
      explanation = "Moderate price swings. Expect some ups and downs, but nothing extreme.";
      color = "text-amber-400";
    } else {
      explanation = "Very volatile — the price can swing dramatically. Only suitable if you're comfortable with risk.";
      color = "text-red-400";
    }
    insights.push({ label: "Price Stability", value: `${(vol * 100).toFixed(0)}% annual swings`, explanation, color });
  }

  const drawdown = riskMetrics.max_drawdown as number | undefined;
  if (drawdown != null) {
    const pct = Math.abs(drawdown * 100);
    let explanation: string;
    let color: string;
    if (pct < 10) {
      explanation = `The worst drop was only ${pct.toFixed(0)}%. This stock has been relatively stable.`;
      color = "text-green-400";
    } else if (pct < 25) {
      explanation = `At its worst, the stock dropped ${pct.toFixed(0)}% from its peak. That's a moderate but recoverable dip.`;
      color = "text-amber-400";
    } else {
      explanation = `The stock once fell ${pct.toFixed(0)}% from its peak. That's a significant drop — recovery can take time.`;
      color = "text-red-400";
    }
    insights.push({ label: "Biggest Historical Drop", value: `${pct.toFixed(0)}% decline`, explanation, color });
  }

  const posSize = riskMetrics.suggested_position_size as number | undefined;
  if (posSize != null) {
    const pct = (posSize * 100).toFixed(0);
    insights.push({
      label: "Suggested Portfolio Allocation",
      value: `${pct}% of your portfolio`,
      explanation: `Based on this stock's risk profile, we suggest investing no more than ${pct}% of your total portfolio in it.`,
      color: posSize > 0.05 ? "text-green-400" : "text-amber-400",
    });
  }

  const sharpe = riskMetrics.sharpe_ratio as number | undefined;
  if (sharpe != null) {
    let explanation: string;
    let color: string;
    if (sharpe > 1) {
      explanation = "Great risk-adjusted returns — you're being well compensated for the risk.";
      color = "text-green-400";
    } else if (sharpe > 0) {
      explanation = "Positive but modest returns relative to the risk involved.";
      color = "text-amber-400";
    } else {
      explanation = "The returns don't justify the risk. You might be better off with safer investments.";
      color = "text-red-400";
    }
    insights.push({ label: "Return vs Risk", value: sharpe.toFixed(2), explanation, color });
  }

  return insights;
}

export default function RiskExplainer({ riskLevel, riskSummary, analystDetails }: RiskExplainerProps) {
  const [expanded, setExpanded] = useState(false);
  const insights = parseRiskMetrics(riskSummary, analystDetails);

  const riskConfig: Record<string, { bg: string; border: string; text: string; label: string; desc: string }> = {
    LOW: {
      bg: "bg-green-500/10", border: "border-green-500/20", text: "text-green-400",
      label: "Low Risk", desc: "This stock shows stable behavior with limited downside risk.",
    },
    MEDIUM: {
      bg: "bg-amber-500/10", border: "border-amber-500/20", text: "text-amber-400",
      label: "Moderate Risk", desc: "This stock has average risk — some price fluctuations are expected.",
    },
    HIGH: {
      bg: "bg-red-500/10", border: "border-red-500/20", text: "text-red-400",
      label: "High Risk", desc: "This stock is volatile. Be prepared for significant price swings.",
    },
  };

  const cfg = riskConfig[riskLevel] ?? riskConfig.MEDIUM;

  return (
    <div className={`rounded-xl ${cfg.bg} border ${cfg.border} p-4 space-y-3`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className={`w-5 h-5 ${cfg.text}`} />
          <div>
            <span className={`font-semibold ${cfg.text}`}>{cfg.label}</span>
            <p className="text-xs text-zinc-400 mt-0.5">{cfg.desc}</p>
          </div>
        </div>
        {insights.length > 0 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-zinc-400 hover:text-white transition-colors"
          >
            {expanded ? "Less" : "Details"}
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        )}
      </div>

      {expanded && insights.length > 0 && (
        <div className="space-y-3 pt-2 border-t border-zinc-700/30">
          {insights.map((insight) => (
            <div key={insight.label} className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-zinc-300">{insight.label}</span>
                <span className={`text-sm font-mono font-semibold ${insight.color}`}>{insight.value}</span>
              </div>
              <p className="text-xs text-zinc-500 leading-relaxed flex items-start gap-1.5">
                <Info className="w-3 h-3 mt-0.5 shrink-0 text-zinc-600" />
                {insight.explanation}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

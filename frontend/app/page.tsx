"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity, Clock, ShieldAlert, Zap, Brain, Cpu, Network,
  ChevronDown, ChevronUp, FileText, Building2, Users, BarChart3,
} from "lucide-react";
import { analyzeStock, checkHealth, ApiError } from "@/lib/api";
import { formatPrice } from "@/lib/currency";
import type { FinalVerdict } from "@/types/api";
import TickerSearch from "@/components/TickerSearch";
import SignalBadge from "@/components/SignalBadge";
import ConfidenceMeter from "@/components/ConfidenceMeter";
import PriceChart from "@/components/PriceChart";
import RiskExplainer from "@/components/RiskExplainer";
import StockReport from "@/components/StockReport";
import AgentCardGrid from "./components/AgentCardGrid";

type HealthState = "checking" | "online" | "offline";

/** Infer display currency from ticker suffix */
function inferCurrency(ticker: string): string {
  const t = ticker.toUpperCase().trim();
  if (t.endsWith(".NS") || t.endsWith(".BO")) return "INR";
  if (t.endsWith(".L")) return "GBP";
  if (t.endsWith(".TO") || t.endsWith(".V")) return "CAD";
  return "USD";
}

/** Format market cap into human-readable form (e.g. $2.8T, ₹15.3L Cr) */
function formatMarketCap(value: number, currency: string = "USD"): string {
  const symbol = currency === "INR" ? "₹" : currency === "GBP" ? "£" : currency === "CAD" ? "C$" : "$";

  if (currency === "INR") {
    // Indian notation: Cr (crore = 10M), L Cr (lakh crore = 1T INR)
    const crore = value / 1e7;
    if (crore >= 1e5) return `${symbol}${(crore / 1e5).toFixed(1)}L Cr`;
    if (crore >= 1) return `${symbol}${crore.toFixed(0)} Cr`;
    return `${symbol}${(value / 1e5).toFixed(0)}L`;
  }

  if (value >= 1e12) return `${symbol}${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `${symbol}${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${symbol}${(value / 1e6).toFixed(0)}M`;
  return `${symbol}${value.toLocaleString()}`;
}

export default function HomePage() {
  const [health, setHealth] = useState<HealthState>("checking");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [verdict, setVerdict] = useState<FinalVerdict | null>(null);
  const [activeTicker, setActiveTicker] = useState("");

  useEffect(() => {
    checkHealth()
      .then(() => setHealth("online"))
      .catch(() => setHealth("offline"));
  }, []);

  async function handleAnalyze(ticker: string) {
    setIsLoading(true);
    setError(null);
    setVerdict(null);
    setActiveTicker(ticker);

    try {
      const result = await analyzeStock(ticker);
      setVerdict(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.statusCode === 400
          ? `Invalid ticker: ${err.detail}`
          : `Server error (${err.statusCode})`);
      } else {
        setError("Network error. Check your connection.");
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-10">
      {/* Hero */}
      <div className="text-center space-y-4 pt-4">
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl md:text-5xl font-bold gradient-text"
        >
          EquityIQ
        </motion.h1>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="text-zinc-400 max-w-xl mx-auto"
        >
          7 AI agents analyze any stock in parallel — fundamentals, momentum, news,
          economy, compliance, and risk — then deliver a clear verdict you can act on.
        </motion.p>

        {/* Tech Badges */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="flex flex-wrap items-center justify-center gap-3"
        >
          {[
            { icon: Network, label: "A2A Protocol" },
            { icon: Brain, label: "Gemini Flash" },
            { icon: Cpu, label: "7 Agents" },
            { icon: Zap, label: "AI Signal Fusion" },
          ].map(({ icon: Icon, label }) => (
            <span
              key={label}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-zinc-800/60 text-zinc-400 border border-zinc-700/50"
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </span>
          ))}
        </motion.div>

        {/* Health Status */}
        <div className="flex items-center justify-center gap-2 text-sm">
          <span className="text-zinc-500">Backend:</span>
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              health === "online"
                ? "bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]"
                : health === "offline"
                  ? "bg-red-500"
                  : "bg-yellow-500 animate-pulse"
            }`}
          />
          <span className="text-zinc-400">
            {health === "online" ? "Online" : health === "offline" ? "Offline" : "Checking..."}
          </span>
        </div>
      </div>

      {/* Ticker Search */}
      <TickerSearch onSubmit={handleAnalyze} isLoading={isLoading} />

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="max-w-xl mx-auto glass rounded-xl p-4 border-red-500/30"
          >
            <p className="text-red-400 text-sm">{error}</p>
            <button
              onClick={() => setError(null)}
              className="text-red-500/60 text-xs mt-2 hover:text-red-400"
            >
              Dismiss
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading - Orchestrator Card */}
      <AnimatePresence>
        {isLoading && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            className="max-w-3xl mx-auto glass rounded-2xl p-6 space-y-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-rose-600 flex items-center justify-center">
                  <Brain className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Analyzing {activeTicker}</h3>
                  <p className="text-xs text-zinc-500">Running 7 AI agents in parallel</p>
                </div>
              </div>
              <div className="glass-dark rounded-lg px-4 py-2 text-center">
                <span className="text-amber-400 font-bold text-lg">{activeTicker}</span>
                <p className="text-[10px] text-zinc-500">Target</p>
              </div>
            </div>

            {/* Progress */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-zinc-400">Checking fundamentals, news, market trends...</span>
                <span className="text-amber-400 pulse-glow">Processing</span>
              </div>
              <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
                <div className="h-full rounded-full bg-gradient-to-r from-amber-500 to-rose-600 shimmer" style={{ width: "60%" }} />
              </div>
            </div>

            {/* What's happening */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "VALUATION", value: "Checking price" },
                { label: "NEWS", value: "Reading articles" },
                { label: "TRENDS", value: "Analyzing charts" },
                { label: "RISK", value: "Assessing safety" },
              ].map(({ label, value }) => (
                <div key={label} className="glass-dark rounded-lg p-3">
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wider">{label}</p>
                  <p className="text-sm font-semibold text-amber-400 mt-0.5">{value}</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results */}
      <AnimatePresence>
        {verdict && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-6"
          >
            {/* Results Header */}
            <div className="max-w-3xl mx-auto glass rounded-2xl p-6 space-y-6">
              {/* Ticker + Signal */}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-3xl font-bold text-white">{verdict.ticker}</h2>
                  {verdict.company_info?.name && (
                    <p className="text-sm text-zinc-400 mt-0.5">{verdict.company_info.name}</p>
                  )}
                  <p className="text-xs text-zinc-500 mt-1">
                    Analysis ID: {verdict.session_id.slice(0, 8)}
                  </p>
                </div>
                <SignalBadge signal={verdict.final_signal} size="lg" />
              </div>

              {/* Company Info */}
              {verdict.company_info && (
                <div className="flex flex-wrap gap-3">
                  {verdict.company_info.market_cap != null && (
                    <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-zinc-800/60 text-zinc-300 border border-zinc-700/50">
                      <BarChart3 className="w-3.5 h-3.5 text-amber-400" />
                      {formatMarketCap(verdict.company_info.market_cap, verdict.company_info.currency)}
                    </span>
                  )}
                  {verdict.company_info.employees != null && (
                    <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-zinc-800/60 text-zinc-300 border border-zinc-700/50">
                      <Users className="w-3.5 h-3.5 text-blue-400" />
                      {verdict.company_info.employees.toLocaleString()} employees
                    </span>
                  )}
                  {verdict.company_info.sector && (
                    <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-zinc-800/60 text-zinc-300 border border-zinc-700/50">
                      <Building2 className="w-3.5 h-3.5 text-green-400" />
                      {verdict.company_info.sector}
                      {verdict.company_info.industry ? ` / ${verdict.company_info.industry}` : ""}
                    </span>
                  )}
                </div>
              )}

              {/* Metrics Row */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard
                  icon={<Activity className="w-4 h-4" />}
                  label="How Confident"
                  value={`${Math.round(verdict.overall_confidence * 100)}%`}
                  sublabel="Agreement across all agents"
                  color={verdict.overall_confidence > 0.6 ? "text-green-400" : verdict.overall_confidence > 0.3 ? "text-amber-400" : "text-red-400"}
                />
                <MetricCard
                  icon={<ShieldAlert className="w-4 h-4" />}
                  label="Risk Level"
                  value={verdict.risk_level === "LOW" ? "Low" : verdict.risk_level === "HIGH" ? "High" : "Medium"}
                  sublabel="Based on volatility & market data"
                  color={verdict.risk_level === "LOW" ? "text-green-400" : verdict.risk_level === "HIGH" ? "text-red-400" : "text-amber-400"}
                />
                <MetricCard
                  icon={<Clock className="w-4 h-4" />}
                  label="Analysis Time"
                  value={verdict.execution_time_ms > 0 ? `${(verdict.execution_time_ms / 1000).toFixed(1)}s` : "N/A"}
                  sublabel="7 agents ran in parallel"
                  color="text-amber-400"
                />
                <MetricCard
                  icon={<Zap className="w-4 h-4" />}
                  label="Price Target"
                  value={verdict.price_target != null ? formatPrice(verdict.price_target, inferCurrency(verdict.ticker)) : "N/A"}
                  sublabel="Estimated fair value"
                  color="text-rose-400"
                />
              </div>

              {/* Confidence Bar */}
              <ConfidenceMeter confidence={verdict.overall_confidence} label="Overall Confidence" />

              {/* Risk Explainer */}
              <RiskExplainer
                riskLevel={verdict.risk_level}
                riskSummary={verdict.risk_summary}
                analystDetails={verdict.analyst_details}
              />

              {/* Quick Agent Summary */}
              {Object.keys(verdict.analyst_signals).length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
                    Agent Signals at a Glance
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(verdict.analyst_signals).map(([agent, signal]) => {
                      const displayName = agent.replace(/([A-Z])/g, " $1").trim();
                      const conf = verdict.analyst_details?.[agent]?.confidence;
                      const confStr = conf != null ? ` (${Math.round(conf * 100)}%)` : "";
                      const color =
                        signal === "BUY" || signal === "STRONG_BUY"
                          ? "text-green-400 bg-green-500/10 border-green-500/20"
                          : signal === "SELL" || signal === "STRONG_SELL"
                            ? "text-red-400 bg-red-500/10 border-red-500/20"
                            : "text-amber-400 bg-amber-500/10 border-amber-500/20";
                      return (
                        <span
                          key={agent}
                          className={`text-xs px-2.5 py-1 rounded-lg border ${color}`}
                        >
                          {displayName}: {signal.replace("_", " ")}{confStr}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Price Chart */}
            <div className="max-w-3xl mx-auto">
              <PriceChart ticker={verdict.ticker} showTypeSelector showCurrencySelector />
            </div>

            {/* Agent Cards */}
            <AgentCardGrid
              signals={verdict.analyst_signals}
              details={verdict.analyst_details}
              ticker={verdict.ticker}
            />

            {/* Collapsible Full Analysis Report */}
            <CollapsibleReport verdict={verdict} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function MetricCard({
  icon, label, value, sublabel, color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sublabel?: string;
  color: string;
}) {
  return (
    <div className="glass-dark rounded-xl p-3 space-y-1">
      <div className="flex items-center gap-1.5 text-zinc-500">
        {icon}
        <span className="text-[10px] uppercase tracking-wider">{label}</span>
      </div>
      <p className={`text-lg font-bold font-mono ${color}`}>{value}</p>
      {sublabel && <p className="text-[10px] text-zinc-600">{sublabel}</p>}
    </div>
  );
}

function CollapsibleReport({ verdict }: { verdict: FinalVerdict }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="max-w-3xl mx-auto">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full glass rounded-xl p-4 flex items-center justify-between hover:border-amber-500/20 transition-all"
      >
        <div className="flex items-center gap-3">
          <FileText className="w-5 h-5 text-amber-400" />
          <div className="text-left">
            <span className="text-sm font-semibold text-white">
              Full Analysis Report
            </span>
            <p className="text-[10px] text-zinc-500">
              Detailed breakdown from all 7 agents with reasoning
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">
            {isOpen ? "Collapse" : "Expand"}
          </span>
          {isOpen ? (
            <ChevronUp className="w-4 h-4 text-amber-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-amber-400" />
          )}
        </div>
      </button>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="mt-3">
              <StockReport verdict={verdict} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

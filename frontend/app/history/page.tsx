"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Clock, Search, Loader2,
} from "lucide-react";
import { getRecentVerdicts } from "@/lib/api";
import { formatPrice } from "@/lib/currency";
import { humanizeText } from "@/lib/metric-labels";
import type { FinalVerdict } from "@/types/api";
import SignalBadge from "@/components/SignalBadge";

/** Infer display currency from ticker suffix */
function inferCurrency(ticker: string): string {
  const t = ticker.toUpperCase().trim();
  if (t.endsWith(".NS") || t.endsWith(".BO")) return "INR";
  if (t.endsWith(".L")) return "GBP";
  if (t.endsWith(".TO") || t.endsWith(".V")) return "CAD";
  return "USD";
}

type FilterTab = "ALL" | "BUY" | "SELL" | "HOLD";

export default function HistoryPage() {
  const [verdicts, setVerdicts] = useState<FinalVerdict[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterTab>("ALL");
  const [selectedVerdict, setSelectedVerdict] = useState<FinalVerdict | null>(null);

  useEffect(() => {
    getRecentVerdicts(50)
      .then(setVerdicts)
      .catch(() => setVerdicts([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = verdicts.filter((v) => {
    if (filter === "ALL") return true;
    if (filter === "BUY") return v.final_signal.includes("BUY");
    if (filter === "SELL") return v.final_signal.includes("SELL");
    return v.final_signal === "HOLD";
  });

  const buyCount = verdicts.filter((v) => v.final_signal.includes("BUY")).length;
  const sellCount = verdicts.filter((v) => v.final_signal.includes("SELL")).length;
  const holdCount = verdicts.filter((v) => v.final_signal === "HOLD").length;
  const avgConfidence = verdicts.length > 0
    ? verdicts.reduce((sum, v) => sum + v.overall_confidence, 0) / verdicts.length
    : 0;

  function timeAgo(ts: string): string {
    const diff = Date.now() - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "Just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  }

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center gap-3">
          <Clock className="w-7 h-7 text-amber-400" />
          <h1 className="text-3xl font-bold gradient-text">Analysis History</h1>
        </div>
        <p className="text-zinc-400 mt-1">
          Track past predictions. Click a row to view detailed analysis.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatCard label="Total" value={String(verdicts.length)} color="text-white" />
        <StatCard label="Buy Signals" value={String(buyCount)} color="text-green-400" />
        <StatCard label="Sell Signals" value={String(sellCount)} color="text-red-400" />
        <StatCard label="Hold Signals" value={String(holdCount)} color="text-amber-400" />
        <StatCard label="Avg Confidence" value={`${Math.round(avgConfidence * 100)}%`} color="text-amber-400" />
      </div>

      <div className="flex gap-2">
        {(["ALL", "BUY", "SELL", "HOLD"] as FilterTab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
              filter === tab
                ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                : "text-zinc-400 hover:text-white border border-transparent hover:bg-zinc-800/50"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 text-amber-400 animate-spin" />
        </div>
      )}

      {!loading && verdicts.length === 0 && (
        <div className="text-center py-16 space-y-3">
          <Search className="w-12 h-12 text-zinc-600 mx-auto" />
          <p className="text-zinc-400">No analyses yet. Go analyze a stock!</p>
        </div>
      )}

      <div className="space-y-3">
        <AnimatePresence>
          {filtered.map((v, i) => (
            <motion.button
              key={v.session_id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              onClick={() => setSelectedVerdict(v)}
              className="w-full glass rounded-xl p-4 flex items-center justify-between gap-4 text-left group"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-xl font-bold text-white shrink-0 max-w-[140px] truncate">{v.ticker}</span>
                <span className="shrink-0">
                  <SignalBadge signal={v.final_signal} size="sm" />
                </span>
                <span className="text-xs text-zinc-500 flex items-center gap-1 shrink-0">
                  <Clock className="w-3 h-3" />
                  {timeAgo(v.timestamp)}
                </span>
              </div>
              <div className="flex items-center gap-6 text-sm">
                <div>
                  <p className="text-[10px] text-zinc-500 uppercase">Confidence</p>
                  <p className="font-mono font-semibold text-amber-400">
                    {Math.round(v.overall_confidence * 100)}%
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-zinc-500 uppercase">Risk</p>
                  <p className={`font-semibold ${
                    v.risk_level === "LOW" ? "text-green-400" :
                    v.risk_level === "HIGH" ? "text-red-400" : "text-amber-400"
                  }`}>
                    {v.risk_level === "LOW" ? "Low" : v.risk_level === "HIGH" ? "High" : "Medium"}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-zinc-500 uppercase">Time</p>
                  <p className="font-mono text-zinc-300">
                    {v.execution_time_ms > 0 ? `${(v.execution_time_ms / 1000).toFixed(1)}s` : "N/A"}
                  </p>
                </div>
              </div>
            </motion.button>
          ))}
        </AnimatePresence>
      </div>

      {/* Detail Modal */}
      <AnimatePresence>
        {selectedVerdict && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
            onClick={() => setSelectedVerdict(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="glass rounded-2xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto space-y-6"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl font-bold text-white">{selectedVerdict.ticker}</span>
                  <SignalBadge signal={selectedVerdict.final_signal} />
                </div>
                <button onClick={() => setSelectedVerdict(null)} className="text-zinc-400 hover:text-white text-xl">
                  &times;
                </button>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="glass-dark rounded-lg p-3">
                  <p className="text-[10px] text-zinc-500 uppercase">Confidence</p>
                  <p className="text-lg font-bold text-amber-400">{Math.round(selectedVerdict.overall_confidence * 100)}%</p>
                </div>
                <div className="glass-dark rounded-lg p-3">
                  <p className="text-[10px] text-zinc-500 uppercase">Risk Level</p>
                  <p className={`text-lg font-bold ${
                    selectedVerdict.risk_level === "LOW" ? "text-green-400" :
                    selectedVerdict.risk_level === "HIGH" ? "text-red-400" : "text-amber-400"
                  }`}>
                    {selectedVerdict.risk_level === "LOW" ? "Low" : selectedVerdict.risk_level === "HIGH" ? "High" : "Medium"}
                  </p>
                </div>
                <div className="glass-dark rounded-lg p-3">
                  <p className="text-[10px] text-zinc-500 uppercase">Analysis Time</p>
                  <p className="text-lg font-bold text-amber-400">
                    {selectedVerdict.execution_time_ms > 0 ? `${(selectedVerdict.execution_time_ms / 1000).toFixed(1)}s` : "N/A"}
                  </p>
                </div>
                <div className="glass-dark rounded-lg p-3">
                  <p className="text-[10px] text-zinc-500 uppercase">Price Target</p>
                  <p className="text-lg font-bold text-rose-400">
                    {selectedVerdict.price_target != null ? formatPrice(selectedVerdict.price_target, inferCurrency(selectedVerdict.ticker)) : "N/A"}
                  </p>
                </div>
              </div>

              {selectedVerdict.key_drivers.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-zinc-500 uppercase">Why This Verdict</h4>
                  <div className="glass-dark rounded-lg p-4 text-sm text-zinc-300 space-y-1">
                    {selectedVerdict.key_drivers
                      .filter((d) => !d.startsWith("WARNING:"))
                      .map((d, i) => (<p key={i}>{d}</p>))}
                  </div>
                </div>
              )}

              {Object.keys(selectedVerdict.analyst_details || {}).length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-zinc-500 uppercase">Agent Breakdown</h4>
                  {Object.entries(selectedVerdict.analyst_details).map(([name, detail]) => (
                    <div key={name} className="glass-dark rounded-lg p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-sm text-white">{name}</span>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-bold ${
                            detail.signal === "BUY" ? "text-green-400" :
                            detail.signal === "SELL" ? "text-red-400" : "text-amber-400"
                          }`}>{detail.signal}</span>
                          <span className="text-xs text-zinc-500">{Math.round(detail.confidence * 100)}%</span>
                        </div>
                      </div>
                      {detail.reasoning && <p className="text-xs text-zinc-400">{humanizeText(detail.reasoning)}</p>}
                      {detail.data_source && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          {detail.data_source}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="glass rounded-xl p-4">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className={`text-2xl font-bold font-mono ${color}`}>{value}</p>
    </div>
  );
}

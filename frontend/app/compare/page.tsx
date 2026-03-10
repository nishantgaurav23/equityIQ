"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus, X, Loader2, BarChart3, GitCompareArrows, Zap, FileText,
  ChevronDown, ChevronUp,
} from "lucide-react";
import { analyzeStock, searchTickers, ApiError } from "@/lib/api";
import type { FinalVerdict, TickerSearchResult } from "@/types/api";
import SignalBadge from "@/components/SignalBadge";
import ConfidenceMeter from "@/components/ConfidenceMeter";
import PriceChart from "@/components/PriceChart";
import StockReport from "@/components/StockReport";
import ComparisonReport from "@/components/ComparisonReport";

const MAX_STOCKS = 5;

interface StockSlot {
  ticker: string;
  verdict: FinalVerdict | null;
  loading: boolean;
  error: string | null;
}

export default function ComparePage() {
  const [slots, setSlots] = useState<StockSlot[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<TickerSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showSearch, setShowSearch] = useState(false);

  const analyzedSlots = slots.filter((s) => s.verdict != null);
  const tickers = analyzedSlots.map((s) => s.ticker);

  async function handleSearch(q: string) {
    setSearchQuery(q);
    if (q.length < 1) { setSearchResults([]); return; }
    setIsSearching(true);
    try {
      const data = await searchTickers(q);
      setSearchResults(data);
    } catch {
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }

  async function addStock(ticker: string) {
    if (slots.length >= MAX_STOCKS) return;
    if (slots.some((s) => s.ticker === ticker)) return;

    setShowSearch(false);
    setSearchQuery("");
    setSearchResults([]);

    const idx = slots.length;
    const newSlot: StockSlot = { ticker, verdict: null, loading: true, error: null };
    setSlots((prev) => [...prev, newSlot]);

    try {
      const result = await analyzeStock(ticker);
      setSlots((prev) =>
        prev.map((s, i) => (i === idx ? { ...s, verdict: result, loading: false } : s))
      );
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : "Analysis failed";
      setSlots((prev) =>
        prev.map((s, i) => (i === idx ? { ...s, error: msg, loading: false } : s))
      );
    }
  }

  function removeStock(ticker: string) {
    setSlots((prev) => prev.filter((s) => s.ticker !== ticker));
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3">
          <GitCompareArrows className="w-7 h-7 text-amber-400" />
          <h1 className="text-3xl font-bold gradient-text">Compare Stocks</h1>
        </div>
        <p className="text-zinc-400 mt-1">
          Add up to {MAX_STOCKS} stocks to compare side by side. See charts, signals, and a combined assessment.
        </p>
      </div>

      {/* Stock Chips + Add Button */}
      <div className="flex flex-wrap items-center gap-3">
        {slots.map((slot) => (
          <div
            key={slot.ticker}
            className={`glass rounded-xl px-4 py-2.5 flex items-center gap-3 ${
              slot.loading ? "animate-pulse" : ""
            }`}
          >
            <span className="font-mono font-bold text-white">{slot.ticker}</span>
            {slot.loading && <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />}
            {slot.verdict && <SignalBadge signal={slot.verdict.final_signal} size="sm" />}
            {slot.error && <span className="text-xs text-red-400">Failed</span>}
            <button
              onClick={() => removeStock(slot.ticker)}
              className="text-zinc-500 hover:text-red-400 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}

        {slots.length < MAX_STOCKS && (
          <div className="relative">
            <button
              onClick={() => setShowSearch(!showSearch)}
              className="glass rounded-xl px-4 py-2.5 flex items-center gap-2 text-zinc-400 hover:text-amber-400 hover:border-amber-500/30 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span className="text-sm">Add Stock</span>
            </button>

            {/* Inline Search Dropdown */}
            <AnimatePresence>
              {showSearch && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  className="absolute z-50 top-full mt-2 w-80 glass-dark rounded-xl overflow-hidden"
                >
                  <div className="p-3">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => handleSearch(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && searchQuery.trim()) {
                          addStock(searchQuery.trim().toUpperCase());
                        }
                        if (e.key === "Escape") setShowSearch(false);
                      }}
                      placeholder="Search ticker or company..."
                      autoFocus
                      className="w-full px-3 py-2 rounded-lg glass-input text-white text-sm placeholder-zinc-500"
                    />
                  </div>
                  {isSearching && (
                    <div className="px-3 pb-3 flex items-center gap-2 text-xs text-zinc-500">
                      <Loader2 className="w-3 h-3 animate-spin" /> Searching...
                    </div>
                  )}
                  {searchResults.map((r) => (
                    <button
                      key={r.ticker}
                      onClick={() => addStock(r.ticker)}
                      disabled={slots.some((s) => s.ticker === r.ticker)}
                      className="w-full px-4 py-2.5 flex items-center justify-between text-left hover:bg-zinc-800/50 transition-colors disabled:opacity-30"
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-mono font-semibold text-amber-400 text-sm w-20 truncate">
                          {r.ticker}
                        </span>
                        <span className="text-sm text-zinc-300 truncate max-w-[180px]">{r.name}</span>
                      </div>
                      <span className="text-[10px] text-zinc-600 uppercase">{r.locale === "in" ? "India" : r.locale === "gb" ? "UK" : "US"}</span>
                    </button>
                  ))}
                  {searchQuery && !isSearching && searchResults.length === 0 && (
                    <div className="px-4 py-3 text-xs text-zinc-500">
                      No results. Press Enter to add &quot;{searchQuery.toUpperCase()}&quot; directly.
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Empty State */}
      {slots.length === 0 && (
        <div className="text-center py-20 space-y-4">
          <BarChart3 className="w-16 h-16 text-zinc-700 mx-auto" />
          <p className="text-zinc-500">Add stocks to start comparing.</p>
          <p className="text-zinc-600 text-sm">
            Supports US stocks (AAPL, MSFT) and Indian stocks (RELIANCE.NS, TCS.NS)
          </p>
        </div>
      )}

      {/* Multi-Stock Price Chart */}
      {tickers.length >= 2 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <PriceChart ticker={tickers} showTypeSelector showCurrencySelector />
        </motion.div>
      )}

      {/* Single stock chart when only 1 analyzed */}
      {tickers.length === 1 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <PriceChart ticker={tickers[0]} showTypeSelector showCurrencySelector />
        </motion.div>
      )}

      {/* Side-by-Side Comparison Cards */}
      {analyzedSlots.length >= 2 && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            Side-by-Side Comparison
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {analyzedSlots.map((slot) => {
              const v = slot.verdict!;
              return (
                <motion.div
                  key={slot.ticker}
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="glass rounded-xl p-5 space-y-4"
                >
                  <div className="flex items-center justify-between">
                    <h4 className="text-xl font-bold text-white">{v.ticker}</h4>
                    <SignalBadge signal={v.final_signal} size="sm" />
                  </div>

                  <ConfidenceMeter confidence={v.overall_confidence} />

                  <div className="grid grid-cols-2 gap-3">
                    <div className="glass-dark rounded-lg p-2.5">
                      <p className="text-[10px] text-zinc-500 uppercase">Risk</p>
                      <p className={`text-sm font-bold ${
                        v.risk_level === "LOW" ? "text-green-400" :
                        v.risk_level === "HIGH" ? "text-red-400" : "text-amber-400"
                      }`}>
                        {v.risk_level === "LOW" ? "Low" : v.risk_level === "HIGH" ? "High" : "Medium"}
                      </p>
                    </div>
                    <div className="glass-dark rounded-lg p-2.5">
                      <p className="text-[10px] text-zinc-500 uppercase">Target</p>
                      <p className="text-sm font-bold text-amber-400 font-mono">
                        {v.price_target != null ? `$${v.price_target.toFixed(2)}` : "N/A"}
                      </p>
                    </div>
                    <div className="glass-dark rounded-lg p-2.5">
                      <p className="text-[10px] text-zinc-500 uppercase">Confidence</p>
                      <p className="text-sm font-bold text-white font-mono">
                        {Math.round(v.overall_confidence * 100)}%
                      </p>
                    </div>
                    <div className="glass-dark rounded-lg p-2.5">
                      <p className="text-[10px] text-zinc-500 uppercase">Agents</p>
                      <p className="text-sm font-bold text-zinc-300">
                        {Object.keys(v.analyst_signals).length} ran
                      </p>
                    </div>
                  </div>

                  {/* Top 3 key drivers */}
                  {v.key_drivers.length > 0 && (
                    <div className="space-y-1">
                      {v.key_drivers
                        .filter((d) => !d.startsWith("WARNING:"))
                        .slice(0, 3)
                        .map((d, i) => (
                          <p key={i} className="text-xs text-zinc-400 flex items-start gap-1.5">
                            <span className="text-amber-500 mt-0.5">&#8226;</span>
                            {d}
                          </p>
                        ))}
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>
        </div>
      )}

      {/* Individual Stock Reports (collapsible) */}
      {analyzedSlots.length >= 1 && (
        <CollapsibleStockReports slots={analyzedSlots} />
      )}

      {/* Combined Assessment Report */}
      {analyzedSlots.length >= 2 && (
        <ComparisonReport verdicts={analyzedSlots.map((s) => s.verdict!)} />
      )}
    </div>
  );
}

function CollapsibleStockReports({ slots }: { slots: StockSlot[] }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="space-y-3">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full glass rounded-xl p-4 flex items-center justify-between hover:border-amber-500/20 transition-all"
      >
        <div className="flex items-center gap-3">
          <FileText className="w-5 h-5 text-amber-400" />
          <div className="text-left">
            <span className="text-sm font-semibold text-white">
              Individual Analysis Reports ({slots.length})
            </span>
            <p className="text-[10px] text-zinc-500">
              Detailed breakdown for each stock
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
            className="overflow-hidden space-y-4"
          >
            {slots.map((slot) => (
              <StockReport key={slot.ticker} verdict={slot.verdict!} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

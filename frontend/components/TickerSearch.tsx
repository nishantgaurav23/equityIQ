"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Loader2, TrendingUp } from "lucide-react";
import { searchTickers } from "@/lib/api";
import type { TickerSearchResult } from "@/types/api";

const POPULAR_TICKERS = [
  { ticker: "AAPL", label: "Apple" },
  { ticker: "GOOGL", label: "Google" },
  { ticker: "RELIANCE.NS", label: "Reliance" },
  { ticker: "TCS.NS", label: "TCS" },
  { ticker: "NVDA", label: "Nvidia" },
  { ticker: "INFY.NS", label: "Infosys" },
];

interface TickerSearchProps {
  onSubmit: (ticker: string) => void;
  isLoading: boolean;
}

export default function TickerSearch({ onSubmit, isLoading }: TickerSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<TickerSearchResult[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 1) {
      setResults([]);
      setShowDropdown(false);
      return;
    }
    setIsSearching(true);
    try {
      const data = await searchTickers(q);
      setResults(data);
      setShowDropdown(data.length > 0);
    } catch {
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(query), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, doSearch]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        !inputRef.current?.contains(e.target as Node)
      ) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleSelect(ticker: string) {
    setQuery(ticker);
    setShowDropdown(false);
    onSubmit(ticker);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!showDropdown) {
      if (e.key === "Enter" && query.trim()) {
        onSubmit(query.trim().toUpperCase());
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => Math.min(prev + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => Math.max(prev - 1, -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (activeIndex >= 0 && results[activeIndex]) {
        handleSelect(results[activeIndex].ticker);
      } else if (query.trim()) {
        setShowDropdown(false);
        onSubmit(query.trim().toUpperCase());
      }
    } else if (e.key === "Escape") {
      setShowDropdown(false);
    }
  }

  return (
    <div className="w-full max-w-xl mx-auto space-y-4">
      {/* Search Input */}
      <div className="relative">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-400" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActiveIndex(-1);
            }}
            onKeyDown={handleKeyDown}
            onFocus={() => results.length > 0 && setShowDropdown(true)}
            placeholder="Search company name or ticker (US & India)..."
            disabled={isLoading}
            className="w-full pl-12 pr-4 py-3.5 rounded-xl glass-input text-white placeholder-zinc-500 text-base"
          />
          {isSearching && (
            <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-amber-400 animate-spin" />
          )}
        </div>

        {/* Dropdown */}
        <AnimatePresence>
          {showDropdown && results.length > 0 && (
            <motion.div
              ref={dropdownRef}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15 }}
              className="absolute z-50 w-full mt-2 rounded-xl glass-dark overflow-hidden"
            >
              {results.map((r, i) => (
                <button
                  key={r.ticker}
                  onClick={() => handleSelect(r.ticker)}
                  onMouseEnter={() => setActiveIndex(i)}
                  className={`w-full px-4 py-3 flex items-center justify-between text-left transition-colors ${
                    i === activeIndex
                      ? "bg-amber-500/10 text-white"
                      : "text-zinc-300 hover:bg-zinc-800/50"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-semibold text-amber-400 text-sm w-20 truncate">
                      {r.ticker}
                    </span>
                    <span className="text-sm truncate max-w-[240px]">{r.name}</span>
                  </div>
                  <span className="text-[10px] text-zinc-600 uppercase">
                    {r.locale === "in" ? "India" : r.locale === "gb" ? "UK" : "US"}
                  </span>
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Analyze Button */}
      <button
        onClick={() => query.trim() && onSubmit(query.trim().toUpperCase())}
        disabled={isLoading || !query.trim()}
        className="w-full py-3.5 rounded-xl font-semibold text-white bg-gradient-to-r from-amber-500 to-rose-600 hover:from-amber-400 hover:to-rose-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 glow-primary"
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="w-5 h-5 animate-spin" />
            Analyzing...
          </span>
        ) : (
          <span className="flex items-center justify-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Analyze with AI Agents
          </span>
        )}
      </button>

      {/* Popular Stocks */}
      <div className="flex flex-wrap items-center justify-center gap-2">
        <span className="text-xs text-zinc-500 mr-1">Popular:</span>
        {POPULAR_TICKERS.map((t) => (
          <button
            key={t.ticker}
            onClick={() => handleSelect(t.ticker)}
            disabled={isLoading}
            className="px-3 py-1 text-xs font-mono rounded-lg bg-zinc-800/60 text-zinc-400 hover:text-white hover:bg-zinc-700/60 border border-zinc-700/50 transition-all disabled:opacity-40"
          >
            {t.label}
          </button>
        ))}
      </div>
    </div>
  );
}

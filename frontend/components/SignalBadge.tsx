"use client";

import type { FinalSignal } from "@/types/api";

const SIGNAL_CONFIG: Record<string, { label: string; bg: string; text: string; glow: string }> = {
  STRONG_BUY: {
    label: "Strong Buy",
    bg: "bg-green-500/20",
    text: "text-green-400",
    glow: "shadow-[0_0_12px_rgba(74,222,128,0.3)]",
  },
  BUY: {
    label: "Buy",
    bg: "bg-green-500/15",
    text: "text-green-400",
    glow: "shadow-[0_0_8px_rgba(74,222,128,0.2)]",
  },
  HOLD: {
    label: "Hold",
    bg: "bg-yellow-500/15",
    text: "text-yellow-400",
    glow: "shadow-[0_0_8px_rgba(251,191,36,0.2)]",
  },
  SELL: {
    label: "Sell",
    bg: "bg-red-500/15",
    text: "text-red-400",
    glow: "shadow-[0_0_8px_rgba(248,113,113,0.2)]",
  },
  STRONG_SELL: {
    label: "Strong Sell",
    bg: "bg-red-500/20",
    text: "text-red-400",
    glow: "shadow-[0_0_12px_rgba(248,113,113,0.3)]",
  },
};

interface SignalBadgeProps {
  signal: FinalSignal | string;
  size?: "sm" | "md" | "lg";
}

export default function SignalBadge({ signal, size = "md" }: SignalBadgeProps) {
  const cfg = SIGNAL_CONFIG[signal] ?? SIGNAL_CONFIG.HOLD;
  const sizeClass = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-3 py-1 text-sm",
    lg: "px-5 py-2 text-lg",
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded-full font-semibold border ${cfg.bg} ${cfg.text} ${cfg.glow} border-current/20 ${sizeClass}`}
    >
      {cfg.label}
    </span>
  );
}

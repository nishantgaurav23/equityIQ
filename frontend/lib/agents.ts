/**
 * Agent metadata registry for the 7 EquityIQ specialist agents.
 * Roles use plain English so non-technical users can understand.
 */

export interface AgentMeta {
  displayName: string;
  role: string;
  icon: string;
  color: string;
  category: string;
}

const AGENT_REGISTRY: Record<string, AgentMeta> = {
  ValuationScout: {
    displayName: "Valuation Scout",
    role: "Is the stock fairly priced?",
    icon: "BarChart3",
    color: "from-amber-500 to-orange-500",
    category: "fundamental",
  },
  MomentumTracker: {
    displayName: "Momentum Tracker",
    role: "Which way is the price trending?",
    icon: "TrendingUp",
    color: "from-rose-500 to-pink-500",
    category: "technical",
  },
  PulseMonitor: {
    displayName: "Pulse Monitor",
    role: "What's the news saying?",
    icon: "Newspaper",
    color: "from-yellow-500 to-amber-500",
    category: "sentiment",
  },
  EconomyWatcher: {
    displayName: "Economy Watcher",
    role: "How's the overall economy?",
    icon: "Globe",
    color: "from-teal-500 to-cyan-500",
    category: "macro",
  },
  ComplianceChecker: {
    displayName: "Compliance Checker",
    role: "Any regulatory red flags?",
    icon: "ShieldCheck",
    color: "from-red-500 to-rose-600",
    category: "regulatory",
  },
  RiskGuardian: {
    displayName: "Risk Guardian",
    role: "How risky is this investment?",
    icon: "ShieldAlert",
    color: "from-zinc-400 to-zinc-500",
    category: "risk",
  },
};

const DEFAULT_META: AgentMeta = {
  displayName: "Unknown Agent",
  role: "Agent details unavailable",
  icon: "HelpCircle",
  color: "from-gray-500 to-gray-600",
  category: "other",
};

export function getAgentMeta(agentName: string): AgentMeta {
  return AGENT_REGISTRY[agentName] ?? DEFAULT_META;
}

export { AGENT_REGISTRY };

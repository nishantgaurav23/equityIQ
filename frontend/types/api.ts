/**
 * TypeScript types matching backend Pydantic models (config/data_contracts.py).
 */

export type Signal = "BUY" | "HOLD" | "SELL";
export type FinalSignal = "STRONG_BUY" | "BUY" | "HOLD" | "SELL" | "STRONG_SELL";
export type MacroRegime = "expansion" | "contraction" | "stagflation" | "recovery";

export interface AnalystReport {
  ticker: string;
  agent_name: string;
  signal: Signal;
  confidence: number;
  reasoning: string;
  timestamp: string;
}

export interface ValuationReport extends AnalystReport {
  pe_ratio: number | null;
  pb_ratio: number | null;
  revenue_growth: number | null;
  debt_to_equity: number | null;
  fcf_yield: number | null;
  intrinsic_value_gap: number | null;
}

export interface MomentumReport extends AnalystReport {
  rsi_14: number | null;
  macd_signal: number | null;
  above_sma_50: boolean | null;
  above_sma_200: boolean | null;
  volume_trend: string | null;
  price_momentum_score: number | null;
}

export interface PulseReport extends AnalystReport {
  sentiment_score: number | null;
  article_count: number;
  top_headlines: string[];
  event_flags: string[];
}

export interface EconomyReport extends AnalystReport {
  gdp_growth: number | null;
  inflation_rate: number | null;
  fed_funds_rate: number | null;
  unemployment_rate: number | null;
  macro_regime: MacroRegime | null;
}

export interface ComplianceReport extends AnalystReport {
  latest_filing_type: string | null;
  days_since_filing: number | null;
  risk_flags: string[];
  risk_score: number | null;
}

export interface RiskGuardianReport extends AnalystReport {
  beta: number | null;
  annualized_volatility: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  suggested_position_size: number | null;
  var_95: number | null;
}

export interface AgentDetail {
  agent_name: string;
  signal: string;
  confidence: number;
  reasoning: string;
  key_metrics: Record<string, unknown>;
  data_source: string;
  execution_time_ms: number;
}

export interface CompanyInfo {
  name: string | null;
  market_cap: number | null;
  employees: number | null;
  sector: string | null;
  industry: string | null;
  currency: string;
}

export interface FinalVerdict {
  ticker: string;
  company_info: CompanyInfo | null;
  final_signal: FinalSignal;
  overall_confidence: number;
  price_target: number | null;
  analyst_signals: Record<string, string>;
  analyst_details: Record<string, AgentDetail>;
  risk_level: string;
  risk_summary: string;
  key_drivers: string[];
  session_id: string;
  execution_time_ms: number;
  timestamp: string;
}

export interface TickerSearchResult {
  ticker: string;
  name: string;
  market: string;
  type: string;
  locale: string;
}

export interface PortfolioInsight {
  tickers: string[];
  verdicts: FinalVerdict[];
  portfolio_signal: FinalSignal;
  diversification_score: number;
  top_pick: string | null;
  timestamp: string;
}

export interface HealthStatus {
  status: string;
  version: string;
}

export interface SignalSnapshot {
  session_id: string;
  ticker: string;
  final_signal: FinalSignal;
  overall_confidence: number;
  created_at: string;
}

export interface ApiErrorResponse {
  detail: string;
  error_type?: string;
}

// Chat types (S16.2)
export interface ChatRequest {
  message: string;
  session_id?: string;
  user_id?: string;
  ticker?: string;
}

export interface ChatEvent {
  type: "session" | "token" | "context" | "done";
  session_id?: string;
  content?: string;
  ticker?: string;
  verdict_session_id?: string;
  full_response?: string;
}

export interface ChatMessage {
  entry_id: string;
  role: "user" | "assistant";
  content: string;
  ticker?: string;
  verdict_session_id?: string;
  created_at: string;
}

export interface ChatHistoryResponse {
  session_id: string;
  messages: ChatMessage[];
}

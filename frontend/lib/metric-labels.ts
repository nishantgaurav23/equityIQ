/**
 * Human-readable labels and explanations for technical financial metrics.
 * Used throughout the frontend to translate jargon into plain English.
 */

/** Map raw metric key -> friendly label */
export const METRIC_LABELS: Record<string, string> = {
  // Valuation
  pe_ratio: "Price vs Earnings",
  pb_ratio: "Price vs Book Value",
  revenue_growth: "Revenue Growth",
  debt_to_equity: "Debt Level",
  fcf_yield: "Free Cash Flow Yield",
  intrinsic_value_gap: "Over/Under Valued",

  // Momentum
  rsi_14: "Momentum Score (RSI)",
  macd_signal: "Trend Direction",
  above_sma_50: "Above 50-Day Average",
  above_sma_200: "Above 200-Day Average",
  volume_trend: "Trading Volume Trend",
  price_momentum_score: "Price Momentum",

  // Sentiment
  sentiment_score: "News Sentiment",
  article_count: "News Articles Found",
  top_headlines: "Top Headlines",
  event_flags: "Notable Events",

  // Economy
  gdp_growth: "Economic Growth (GDP)",
  inflation_rate: "Inflation Rate",
  fed_funds_rate: "Fed Interest Rate",
  unemployment_rate: "Unemployment Rate",
  macro_regime: "Economic Phase",

  // Compliance
  latest_filing_type: "Latest SEC Filing",
  days_since_filing: "Days Since Filing",
  risk_flags: "Regulatory Warnings",
  risk_score: "Compliance Risk",

  // Risk
  beta: "Market Sensitivity",
  annualized_volatility: "Price Swings",
  sharpe_ratio: "Risk-Adjusted Return",
  max_drawdown: "Biggest Drop",
  suggested_position_size: "Suggested Investment",
  var_95: "Worst-Case Daily Loss",
};

/** Tooltip explanations for key metrics */
export const METRIC_TOOLTIPS: Record<string, string> = {
  pe_ratio:
    "How much investors pay per $1 of company earnings. Lower = potentially cheaper stock.",
  pb_ratio:
    "Stock price compared to what the company owns. Under 1 means it might be undervalued.",
  revenue_growth:
    "How fast the company's sales are growing. Positive = business is expanding.",
  debt_to_equity:
    "How much the company borrows vs owns. Lower = less risky finances.",
  fcf_yield:
    "Cash left after expenses as % of stock price. Higher = more cash being generated.",
  intrinsic_value_gap:
    "Whether the stock is priced above or below its estimated true value.",
  rsi_14:
    "Measures recent price momentum (0-100). Above 70 = overbought, below 30 = oversold.",
  macd_signal:
    "Shows whether the price trend is strengthening or weakening.",
  above_sma_50:
    "Whether the stock is trading above its 50-day average price — a bullish sign.",
  above_sma_200:
    "Whether the stock is above its 200-day average — indicates long-term uptrend.",
  volume_trend:
    "Whether more or fewer shares are being traded recently.",
  price_momentum_score:
    "Overall score combining multiple momentum indicators.",
  sentiment_score:
    "How positive or negative recent news coverage is (-1 to +1).",
  article_count:
    "Number of recent news articles analyzed for this stock.",
  gdp_growth: "How fast the overall economy is growing. Positive = healthy economy.",
  inflation_rate:
    "How fast prices are rising. High inflation often leads to higher interest rates.",
  fed_funds_rate:
    "The interest rate set by the Federal Reserve. Higher = borrowing costs more.",
  unemployment_rate:
    "Percentage of people looking for work. Lower = stronger economy.",
  macro_regime:
    "Current phase of the economic cycle: expansion, contraction, recovery, or stagflation.",
  beta:
    "How much this stock moves relative to the market. 1 = same as market, >1 = more volatile, <1 = steadier.",
  annualized_volatility:
    "How wildly the stock price swings over a year. Higher = more unpredictable.",
  sharpe_ratio:
    "Return earned per unit of risk. Higher = better risk-adjusted performance.",
  max_drawdown:
    "The largest peak-to-trough drop. Shows the worst-case loss you could have experienced.",
  suggested_position_size:
    "What % of your portfolio to invest in this stock, based on its risk level.",
  var_95:
    "The most you'd likely lose in a single day, 95% of the time.",
};

/** Format a metric value for display */
export function formatMetricValue(key: string, value: unknown): string {
  if (value == null || value === "") return "N/A";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.length > 0 ? value.join(", ") : "None";

  if (typeof value === "number") {
    // Economy metrics from FRED — already in percentage form (e.g., 4.1667 = 4.1667%)
    // Do NOT multiply by 100 again.
    const ALREADY_PERCENTAGE_KEYS = [
      "gdp_growth",
      "inflation_rate",
      "fed_funds_rate",
      "unemployment_rate",
    ];
    if (ALREADY_PERCENTAGE_KEYS.includes(key)) {
      return `${value.toFixed(1)}%`;
    }

    // Risk/valuation metrics — stored as decimal fractions (0.25 = 25%)
    // These DO need multiplication by 100.
    if (
      key === "var_95" ||
      key === "max_drawdown" ||
      key === "annualized_volatility" ||
      key === "suggested_position_size" ||
      key === "revenue_growth" ||
      key === "fcf_yield" ||
      key === "intrinsic_value_gap"
    ) {
      return `${(value * 100).toFixed(1)}%`;
    }

    // Compliance risk_score (0-1 range, display as percentage)
    if (key === "risk_score") {
      return `${(value * 100).toFixed(0)}%`;
    }

    // Scores (0-1 range)
    if (key.includes("score") || key === "sentiment_score") {
      return value.toFixed(2);
    }
    // Ratios
    if (key.includes("ratio") || key === "beta" || key === "sharpe_ratio") {
      return value.toFixed(2);
    }
    // Days
    if (key === "days_since_filing" || key === "article_count") {
      return String(Math.round(value));
    }
    return value.toFixed(2);
  }

  // Macro regime
  if (key === "macro_regime") {
    const labels: Record<string, string> = {
      expansion: "Growing Economy",
      contraction: "Slowing Economy",
      stagflation: "Stagnant Economy",
      recovery: "Recovering Economy",
    };
    return labels[String(value)] ?? String(value);
  }

  return String(value);
}

/** Known snake_case terms that appear in agent reasoning — map to readable form */
const HUMANIZE_MAP: Record<string, string> = {
  going_concern: "going concern",
  sebi_investigation: "SEBI investigation",
  material_weakness: "material weakness",
  delisting_risk: "delisting risk",
  insider_trading: "insider trading",
  related_party: "related party",
  late_filing: "late filing",
  risk_flags: "risk flags",
  risk_score: "risk score",
  macro_regime: "economic regime",
  debt_to_equity: "debt-to-equity",
  fcf_yield: "free cash flow yield",
  pe_ratio: "P/E ratio",
  pb_ratio: "P/B ratio",
  revenue_growth: "revenue growth",
  intrinsic_value_gap: "intrinsic value gap",
  price_momentum_score: "price momentum score",
  fed_funds_rate: "fed funds rate",
};

/**
 * Clean up snake_case terms in free-text reasoning for display.
 * Replaces known terms with their human-readable equivalents,
 * and converts any remaining snake_case words to spaced words.
 */
export function humanizeText(text: string): string {
  let result = text;
  // Replace known terms first (longer matches first to avoid partial replacements)
  const sorted = Object.entries(HUMANIZE_MAP).sort(
    ([a], [b]) => b.length - a.length
  );
  for (const [snake, human] of sorted) {
    // Use word-boundary-aware replacement (handle quotes, parens, etc.)
    result = result.replace(
      new RegExp(`(?<=['"\`(\\s,;:]|^)${snake.replace(/_/g, "_")}(?=['"\`),;:\\s.]|$)`, "g"),
      human
    );
  }
  // Catch any remaining snake_case words (2+ segments) not in the map
  result = result.replace(/\b([a-z]+(?:_[a-z]+)+)\b/g, (match) => {
    return match.replace(/_/g, " ");
  });
  return result;
}

/** India-specific label overrides */
const INDIA_METRIC_LABELS: Record<string, string> = {
  fed_funds_rate: "RBI Repo Rate",
  latest_filing_type: "Latest Corporate Filing",
};

/** India-specific tooltip overrides */
const INDIA_METRIC_TOOLTIPS: Record<string, string> = {
  fed_funds_rate:
    "The repo rate set by the Reserve Bank of India. Higher = borrowing costs more.",
  latest_filing_type:
    "The most recent corporate filing from NSE/BSE.",
};

/** Check if a ticker is Indian (.NS or .BO suffix) */
function isIndianTicker(ticker: string): boolean {
  const t = ticker.toUpperCase().trim();
  return t.endsWith(".NS") || t.endsWith(".BO");
}

/** Get a friendly label for a metric key, with optional Indian market context */
export function getMetricLabel(key: string, ticker?: string): string {
  if (ticker && isIndianTicker(ticker) && INDIA_METRIC_LABELS[key]) {
    return INDIA_METRIC_LABELS[key];
  }
  return METRIC_LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Get tooltip for a metric key, with optional Indian market context */
export function getMetricTooltip(key: string, ticker?: string): string | undefined {
  if (ticker && isIndianTicker(ticker) && INDIA_METRIC_TOOLTIPS[key]) {
    return INDIA_METRIC_TOOLTIPS[key];
  }
  return METRIC_TOOLTIPS[key];
}

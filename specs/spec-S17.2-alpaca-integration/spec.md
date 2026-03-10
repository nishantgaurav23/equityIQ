# S17.2 -- Alpaca Broker Integration (US)

## Overview
Integrate with Alpaca's Trading API to fetch user positions and account balance, support paper trading, and map Alpaca symbols to EquityIQ tickers. Optional: place paper orders based on STRONG_BUY/STRONG_SELL signals.

## Dependencies
- **S9.2** (Portfolio endpoint) -- `done`
- **S8.3** (Portfolio analyzer) -- `done`

## Location
- `integrations/alpaca.py` -- Main Alpaca integration module
- `tests/test_alpaca.py` -- Test suite
- `api/alpaca_routes.py` -- API endpoints
- `config/settings.py` -- Add Alpaca config fields

## Requirements

### R1: Settings Configuration
Add to `config/settings.py`:
- `ALPACA_API_KEY: str = ""` -- Alpaca API key
- `ALPACA_API_SECRET: str = ""` -- Alpaca API secret
- `ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"` -- Base URL (paper trading default)
- `ALPACA_DATA_URL: str = "https://data.alpaca.markets"` -- Market data URL

### R2: Authentication
Alpaca uses API key + secret in headers (no OAuth2 flow needed):
- Headers: `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY`
- Support both paper (`paper-api.alpaca.markets`) and live (`api.alpaca.markets`) base URLs
- `get_account()` -- Verify credentials and return account info (buying power, portfolio value, etc.)

### R3: Fetch Positions
- `get_positions() -> list[AlpacaPosition]`
- Returns current open positions with: symbol, qty, avg_entry_price, current_price, market_value, unrealized_pl, unrealized_plpc, side (long/short)
- Symbol is already in EquityIQ format for US stocks (e.g., AAPL)

### R4: Fetch Account
- `get_account() -> AlpacaAccount`
- Returns: account_id, buying_power, portfolio_value, cash, equity, last_equity, day_trade_count, pattern_day_trader status

### R5: Symbol Mapping
- `map_alpaca_to_equityiq(symbol: str) -> str`
  - US stocks: symbol as-is (e.g., AAPL -> AAPL)
  - Handle class B shares: BRK.B -> BRK-B (if needed)
- `map_equityiq_to_alpaca(ticker: str) -> str`
  - Strip any suffix if present (e.g., AAPL -> AAPL)
  - Handle Indian tickers gracefully: return "" for .NS/.BO

### R6: Portfolio Summary
- `get_portfolio_summary() -> AlpacaPortfolio`
- Aggregates positions + account into portfolio summary:
  - Total portfolio value
  - Buying power / cash available
  - Total unrealized P&L (absolute + percentage)
  - Day P&L
  - List of mapped EquityIQ tickers for analysis

### R7: Paper Order Placement (Optional)
- `place_paper_order(symbol: str, qty: int, side: str, order_type: str = "market") -> AlpacaOrder`
- Only allowed when base URL is paper-api (safety check)
- Supports: market orders, limit orders
- Returns order confirmation with order_id, status, filled_qty
- Safety: requires explicit `allow_paper_trading=True` in settings

### R8: API Endpoints
Add `api/alpaca_routes.py`:
- `GET /api/v1/alpaca/account` -- Account info (requires API key headers or stored creds)
- `GET /api/v1/alpaca/positions` -- Fetch positions
- `GET /api/v1/alpaca/portfolio` -- Full portfolio summary
- `POST /api/v1/alpaca/analyze` -- Analyze Alpaca holdings via EquityIQ
- `POST /api/v1/alpaca/paper-order` -- Place paper order (optional, gated)

### R9: Error Handling
- All Alpaca API calls wrapped in try/except
- Handle: 401 (invalid credentials), 403 (forbidden), 422 (invalid request), 429 (rate limit)
- Return structured error responses with appropriate HTTP status codes
- Graceful degradation: if Alpaca API is down, return cached data if available

### R10: Rate Limiting & Caching
- Alpaca allows 200 requests/minute
- TTL cache on positions (15-second TTL) and account (15-second TTL)
- Implement via cachetools.TTLCache

## Data Models

```python
class AlpacaPosition(BaseModel):
    symbol: str
    qty: float  # Can be fractional
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pl: float
    unrealized_plpc: float  # Percentage
    side: str  # "long" or "short"
    equityiq_ticker: str  # Mapped ticker

class AlpacaAccount(BaseModel):
    account_id: str
    buying_power: float
    portfolio_value: float
    cash: float
    equity: float
    last_equity: float
    day_trade_count: int
    pattern_day_trader: bool
    trading_blocked: bool
    account_blocked: bool

class AlpacaOrder(BaseModel):
    order_id: str
    symbol: str
    qty: float
    side: str  # "buy" or "sell"
    order_type: str  # "market", "limit"
    status: str  # "new", "filled", "partially_filled", "cancelled"
    filled_qty: float = 0.0
    filled_avg_price: float = 0.0
    submitted_at: datetime

class AlpacaPortfolio(BaseModel):
    positions: list[AlpacaPosition]
    account: AlpacaAccount
    portfolio_value: float
    buying_power: float
    total_unrealized_pl: float
    total_unrealized_plpc: float
    day_pl: float
    equityiq_tickers: list[str]
    connected_at: datetime
```

## Security
- Never log or store API keys/secrets in plain text
- API credentials passed via `X-Alpaca-Key` and `X-Alpaca-Secret` headers, not query params
- Paper order placement gated behind `ALPACA_ALLOW_PAPER_TRADING` setting
- Live trading never allowed (hard-coded safety check)

## Testing Strategy
- Mock all Alpaca API calls (httpx responses)
- Test API key authentication (header construction)
- Test positions parsing with sample Alpaca API responses
- Test account info parsing
- Test portfolio summary aggregation
- Test symbol mapping (US stocks, class B shares, Indian ticker rejection)
- Test paper order placement (when enabled and disabled)
- Test error handling (invalid creds, network errors, rate limiting)
- Test safety checks (no live trading, paper order gating)

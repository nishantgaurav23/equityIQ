# S17.1 -- Zerodha Broker Integration (India)

## Overview
Integrate with Zerodha's Kite Connect API to fetch user holdings and positions, display portfolio with live P&L, and map Zerodha symbols to EquityIQ tickers (.NS/.BO). Read-only initially -- no order placement.

## Dependencies
- **S9.2** (Portfolio endpoint) -- `done`
- **S8.3** (Portfolio analyzer) -- `done`

## Location
- `integrations/zerodha.py` -- Main Zerodha integration module
- `integrations/__init__.py` -- Package init
- `tests/test_zerodha.py` -- Test suite
- `config/settings.py` -- Add Zerodha config fields

## Requirements

### R1: Settings Configuration
Add to `config/settings.py`:
- `ZERODHA_API_KEY: str = ""` -- Kite Connect API key
- `ZERODHA_API_SECRET: str = ""` -- Kite Connect API secret
- `ZERODHA_REDIRECT_URL: str = "http://localhost:8000/api/v1/zerodha/callback"` -- OAuth2 redirect URL

### R2: OAuth2 Login Flow
Implement Kite Connect OAuth2 flow:
1. `get_login_url()` -- Returns Zerodha login URL for user to authenticate
2. `exchange_request_token(request_token: str)` -- Exchanges request token for access token
3. Access token stored in-memory (per-session) with expiry tracking
4. Tokens expire daily (Zerodha resets at ~6:00 AM IST)

### R3: Fetch Holdings
- `get_holdings(access_token: str) -> list[ZerodhaHolding]`
- Returns list of delivery holdings (CNC) with: tradingsymbol, exchange, quantity, average_price, last_price, pnl, day_change_percentage
- Map Zerodha exchange (NSE/BSE) to EquityIQ suffix (.NS/.BO)

### R4: Fetch Positions
- `get_positions(access_token: str) -> list[ZerodhaPosition]`
- Returns day + net positions with: tradingsymbol, exchange, product, quantity, buy_price, sell_price, pnl
- Separate day positions from net positions

### R5: Symbol Mapping
- `map_zerodha_to_equityiq(tradingsymbol: str, exchange: str) -> str`
  - NSE -> `.NS` suffix (e.g., RELIANCE -> RELIANCE.NS)
  - BSE -> `.BO` suffix (e.g., RELIANCE -> RELIANCE.BO)
  - Handle special cases: NIFTY 50 options/futures (skip non-equity)
- `map_equityiq_to_zerodha(ticker: str) -> tuple[str, str]`
  - Reverse mapping: RELIANCE.NS -> (RELIANCE, NSE)

### R6: Portfolio Summary
- `get_portfolio_summary(access_token: str) -> ZerodhaPortfolio`
- Aggregates holdings into portfolio summary:
  - Total invested value
  - Current value
  - Total P&L (absolute + percentage)
  - Day P&L
  - List of mapped EquityIQ tickers for analysis

### R7: API Endpoints
Add to `api/routes.py` or new `api/zerodha_routes.py`:
- `GET /api/v1/zerodha/login` -- Returns login URL
- `GET /api/v1/zerodha/callback` -- OAuth2 callback, exchanges token
- `GET /api/v1/zerodha/holdings` -- Fetch holdings (requires access_token header)
- `GET /api/v1/zerodha/positions` -- Fetch positions
- `GET /api/v1/zerodha/portfolio` -- Full portfolio summary
- `POST /api/v1/zerodha/analyze` -- Analyze Zerodha holdings via EquityIQ

### R8: Error Handling
- All Kite Connect API calls wrapped in try/except
- Handle: TokenException (expired/invalid token), NetworkException, InputException
- Return structured error responses with appropriate HTTP status codes
- Graceful degradation: if Kite API is down, return cached data if available

### R9: Rate Limiting Awareness
- Kite Connect allows 3 requests/second per API key
- Implement simple rate limiting via asyncio.Semaphore or token bucket
- TTL cache on holdings/positions (30-second TTL during market hours)

## Data Models

```python
class ZerodhaHolding(BaseModel):
    tradingsymbol: str
    exchange: str  # NSE or BSE
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    day_change_percentage: float
    equityiq_ticker: str  # Mapped ticker (e.g., RELIANCE.NS)

class ZerodhaPosition(BaseModel):
    tradingsymbol: str
    exchange: str
    product: str  # CNC, MIS, NRML
    quantity: int
    buy_price: float
    sell_price: float
    pnl: float
    equityiq_ticker: str

class ZerodhaPortfolio(BaseModel):
    holdings: list[ZerodhaHolding]
    positions: list[ZerodhaPosition]
    total_invested: float
    current_value: float
    total_pnl: float
    total_pnl_percentage: float
    day_pnl: float
    equityiq_tickers: list[str]  # For bulk analysis
    connected_at: datetime
```

## Security
- Never log or store API secrets or access tokens in plain text
- Access tokens passed via `X-Zerodha-Token` header, not query params
- API secret used only for token exchange, never sent to frontend

## Testing Strategy
- Mock all Kite Connect API calls (httpx responses)
- Test OAuth2 flow (login URL generation, token exchange)
- Test symbol mapping (NSE/BSE -> .NS/.BO and reverse)
- Test holdings/positions parsing with sample Kite API responses
- Test portfolio summary aggregation
- Test error handling (expired token, network errors, invalid responses)
- Test rate limiting behavior

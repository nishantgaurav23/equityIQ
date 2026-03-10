"""Custom exception hierarchy for EquityIQ API."""


class EquityIQError(Exception):
    """Base exception for all EquityIQ domain errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        details: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class InvalidTickerError(EquityIQError):
    """Ticker format is invalid (too long, empty, bad characters)."""

    def __init__(self, ticker: str, details: dict | None = None):
        super().__init__(
            message=f"Invalid ticker symbol: {ticker!r}",
            error_code="INVALID_TICKER",
            details=details,
        )


class TickerNotFoundError(EquityIQError):
    """Ticker doesn't exist or has no available data."""

    def __init__(self, ticker: str, details: dict | None = None):
        super().__init__(
            message=f"Ticker {ticker!r} not found or has no available data",
            error_code="TICKER_NOT_FOUND",
            details=details,
        )


class AnalysisTimeoutError(EquityIQError):
    """Analysis pipeline or agent exceeded timeout."""

    def __init__(self, ticker: str, details: dict | None = None):
        super().__init__(
            message=f"Analysis timed out for ticker {ticker!r}",
            error_code="ANALYSIS_TIMEOUT",
            details=details,
        )


class InsufficientDataError(EquityIQError):
    """Not enough data to produce a reliable analysis."""

    def __init__(self, ticker: str, details: dict | None = None):
        super().__init__(
            message=f"Insufficient data to analyze ticker {ticker!r}",
            error_code="INSUFFICIENT_DATA",
            details=details,
        )


class VerdictNotFoundError(EquityIQError):
    """Session ID lookup returned no verdict."""

    def __init__(self, session_id: str, details: dict | None = None):
        super().__init__(
            message=f"Verdict not found for session {session_id!r}",
            error_code="VERDICT_NOT_FOUND",
            details=details,
        )

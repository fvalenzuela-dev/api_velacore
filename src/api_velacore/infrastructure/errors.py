class MarketDataProviderError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        """Create a normalized market data provider error."""
        self.message = message
        self.status_code = status_code
        super().__init__(message)

"""Real-world data providers for device simulation."""
from backend.src.streaming.providers.weather import WeatherProvider
from backend.src.streaming.providers.market_prices import MarketPriceProvider

__all__ = ["WeatherProvider", "MarketPriceProvider"]

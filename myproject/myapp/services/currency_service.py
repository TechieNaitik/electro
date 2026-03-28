import requests
import os
import logging
from django.core.cache import cache
from datetime import datetime

logger = logging.getLogger(__name__)

class CurrencyService:
    BASE_URL = "https://v6.exchangerate-api.com/v6"
    CACHE_KEY = "exchange_rates"
    CACHE_TTL = 3600  # 60 minutes (3600 seconds)

    # Fallback rates if API is unavailable (approximate)
    DEFAULT_RATES = {
        "USD": 1.0,
        "INR": 83.0,
        "EUR": 0.92,
        "GBP": 0.79,
        "JPY": 151.0,
        "CAD": 1.35,
        "AUD": 1.52
    }

    @classmethod
    def get_rates(cls, force_refresh=False):
        # API Key management via environment variables
        api_key = os.getenv("EXCHANGE_RATE_API_KEY")
        
        # 1. In-memory Caching (L1 - Django Cache)
        # Skip cache check if force_refresh is True
        if not force_refresh:
            cached_data = cache.get(cls.CACHE_KEY)
            if cached_data:
                logger.info("CurrencyService: L1 Cache Hit.")
                return cached_data

        logger.info("CurrencyService: L1 Cache Miss. Fetching from API.")
        
        if not api_key:
            logger.warning("EXCHANGE_RATE_API_KEY not found in .env. Using fallback rates.")
            rates_data = {
                "rates": cls.DEFAULT_RATES,
                "base": "USD",
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "stale": True,
                "source": "fallback"
            }
            return rates_data

        try:
            # Singleton fetch pattern - could be enhanced with a lock if high concurrency is expected
            url = f"{cls.BASE_URL}/{api_key}/latest/USD"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            if data.get("result") == "success":
                rates_data = {
                    "rates": data.get("conversion_rates"),
                    "base": "USD",
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "stale": False,
                    "source": "api"
                }
                # Store in L1 cache for 60 minutes
                cache.set(cls.CACHE_KEY, rates_data, cls.CACHE_TTL)
                return rates_data
            else:
                raise ValueError(f"API Error: {data.get('error-type', 'Unknown error')}")

        except Exception as e:
            logger.error(f"CurrencyService: API fetch failed: {str(e)}")
            # Graceful degradation: Return defaults with stale flag
            return {
                "rates": cls.DEFAULT_RATES,
                "base": "USD",
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "stale": True,
                "source": "error-fallback",
                "error": str(e)
            }

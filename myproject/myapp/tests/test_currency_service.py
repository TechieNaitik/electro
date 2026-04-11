import pytest
import requests
from unittest.mock import patch, MagicMock
from django.core.cache import cache
from myapp.services.currency_service import CurrencyService

@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()

class TestCurrencyService:
    @patch('myapp.services.currency_service.requests.get')
    def test_get_rates_api_success(self, mock_get):
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": "success",
            "conversion_rates": {"INR": 83.5, "EUR": 0.93}
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with patch('os.getenv', return_value='fake_key'):
            rates = CurrencyService.get_rates()
            
            assert rates['source'] == 'api'
            assert rates['rates']['INR'] == 83.5
            assert rates['stale'] is False
            
            # Verify cache is set
            assert cache.get(CurrencyService.CACHE_KEY) == rates

    @patch('myapp.services.currency_service.cache.get')
    def test_get_rates_cache_hit(self, mock_cache_get):
        # Mock cache hit
        cached_data = {"rates": {"INR": 84.0}, "source": "api"}
        mock_cache_get.return_value = cached_data
        
        rates = CurrencyService.get_rates()
        assert rates == cached_data
        assert rates['source'] == 'api'

    def test_get_rates_no_api_key(self):
        with patch('os.getenv', return_value=None):
            rates = CurrencyService.get_rates()
            assert rates['source'] == 'fallback'
            assert rates['stale'] is True
            assert rates['rates'] == CurrencyService.DEFAULT_RATES

    @patch('myapp.services.currency_service.requests.get')
    def test_get_rates_api_error(self, mock_get):
        # Mock API error
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "error", "error-type": "invalid-key"}
        mock_get.return_value = mock_response
        
        with patch('os.getenv', return_value='fake_key'):
            rates = CurrencyService.get_rates()
            assert rates['source'] == 'error-fallback'
            assert rates['stale'] is True
            assert 'invalid-key' in rates['error']

    @patch('myapp.services.currency_service.requests.get')
    def test_get_rates_exception(self, mock_get):
        # Mock network exception
        mock_get.side_effect = Exception("Connection Timeout")
        
        with patch('os.getenv', return_value='fake_key'):
            rates = CurrencyService.get_rates()
            assert rates['source'] == 'error-fallback'
            assert 'Connection Timeout' in rates['error']

    @patch('myapp.services.currency_service.requests.get')
    def test_force_refresh(self, mock_get):
        # Set cache
        cache.set(CurrencyService.CACHE_KEY, {"old": "data"})
        
        # Mock success
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "success", "conversion_rates": {"NEW": 1.0}}
        mock_get.return_value = mock_response
        
        with patch('os.getenv', return_value='fake_key'):
            rates = CurrencyService.get_rates(force_refresh=True)
            assert "NEW" in rates['rates']
            assert mock_get.called

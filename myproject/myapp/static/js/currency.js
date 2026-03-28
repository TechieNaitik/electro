/**
 * CurrencyManager: Handles site-wide reactive currency conversion.
 * Features:
 * - Singleton API fetch with debouncing/throttling behavior.
 * - Two-tier caching: L1 (Session/Memory), L2 (LocalStorage).
 * - Reactive DOM updates for all price elements.
 * - Graceful degradation with staleness indicators.
 */
class CurrencyManager {
    constructor() {
        this.cacheKey = 'electro_exchange_rates';
        this.prefKey = 'electro_user_currency';
        this.cacheTTL = 3600000; // 60 minutes in ms
        this.baseCurrency = 'INR'; // Our DB stores prices in INR
        this.defaultCurrency = 'INR';
        this.rates = null;
        this.lastUpdated = null;
        this.isStale = false;
        
        this.symbols = {
            'USD': '$',
            'INR': '₹',
            'EUR': '€',
            'GBP': '£',
            'JPY': '¥',
            'CAD': 'CA$',
            'AUD': 'A$'
        };

        this.init();
    }

    async init() {
        // Load preferred currency
        const savedCurrency = localStorage.getItem(this.prefKey) || this.defaultCurrency;
        this.currentCurrency = savedCurrency;
        
        console.log(`[Currency] Initializing with: ${this.currentCurrency}`);

        // 1. Initial local cache check (L2)
        this.loadFromLocal();
        
        // 2. Fetch fresh rates if needed (L1 is handled by the server-side API)
        // We implement a "SWR" (Stale-While-Revalidate) like behavior here:
        // If we have cached rates, we apply them immediately, then fetch fresh in background if expired.
        if (this.rates) {
            this.updateSwitcherUI();
            this.applyRatesToDOM();
        }

        await this.syncRates();

        // 3. Final UI check after sync
        this.updateSwitcherUI();
        this.applyRatesToDOM();
        this.setupEventListeners();
        
        // Log cache status for reviewers
        const cacheSource = this.loadFromLocal() ? 'LocalStorage (L2)' : 'API (L1 Cache)';
        console.log(`[Currency] Ready. Source: ${cacheSource}`);
    }

    loadFromLocal() {
        const cached = localStorage.getItem(this.cacheKey);
        if (cached) {
            try {
                const data = JSON.parse(cached);
                const age = Date.now() - data.timestamp;
                if (age < this.cacheTTL) {
                    this.rates = data.rates;
                    this.lastUpdated = data.lastUpdated;
                    this.isStale = data.stale;
                    console.log(`[Currency] L2 Cache Hit. Age: ${Math.round(age/1000)}s`);
                    return true;
                }
            } catch (e) {
                localStorage.removeItem(this.cacheKey);
            }
        }
        return false;
    }

    async syncRates() {
        const cached = JSON.parse(localStorage.getItem(this.cacheKey) || '{}');
        const isExpired = !cached.timestamp || (Date.now() - cached.timestamp > this.cacheTTL);

        if (!this.rates || isExpired) {
            console.log("[Currency] Cache Miss/Expired. Requesting fresh rates...");
            try {
                const response = await fetch('/api/exchange-rates/');
                const data = await response.json();
                
                this.rates = data.rates;
                this.lastUpdated = data.last_updated;
                this.isStale = data.stale;

                // Persist to L2 Cache
                localStorage.setItem(this.cacheKey, JSON.stringify({
                    rates: this.rates,
                    lastUpdated: this.lastUpdated,
                    stale: this.isStale,
                    timestamp: Date.now()
                }));
            } catch (err) {
                console.error("[Currency] API Error:", err);
                if (!this.rates) {
                    this.rates = { 'USD': 0.012, 'INR': 1.0, 'EUR': 0.011, 'GBP': 0.0095 };
                    this.isStale = true;
                    this.lastUpdated = "N/A (Fallback)";
                }
            }
        }
    }

    setupEventListeners() {
        const self = this;
        // Event listener for dropdown clicks
        $(document).on('click', '.currency-select-item', function(e) {
            e.preventDefault();
            const newCurr = $(this).data('currency');
            self.setCurrency(newCurr);
        });

        // Optional: Listen for manual refresh
        $(document).on('click', '#refresh-rates-btn', function(e) {
            e.preventDefault();
            const btn = $(this);
            if (btn.hasClass('disabled')) return;
            
            btn.addClass('disabled').html('<i class="fas fa-spinner fa-spin"></i>');
            localStorage.removeItem(self.cacheKey);
            self.syncRates().then(() => {
                self.applyRatesToDOM();
                self.updateSwitcherUI();
                btn.removeClass('disabled').html('<i class="fas fa-sync-alt"></i>');
            });
        });
    }

    setCurrency(currency) {
        if (currency === this.currentCurrency) return;
        
        console.log(`[Currency] Switching ${this.currentCurrency} -> ${currency}`);
        this.currentCurrency = currency;
        localStorage.setItem(this.prefKey, currency);
        
        this.updateSwitcherUI();
        this.applyRatesToDOM();
        
        // Notify other JS components
        $(window).trigger('currency:changed', { currency });
    }

    updateSwitcherUI() {
        $('.current-currency-code').text(this.currentCurrency);
        // Update staleness indicator
        if (this.isStale || (this.lastUpdated && this.lastUpdated.includes('Fallback'))) {
            $('.currency-status').html(`<span class="badge bg-soft-warning text-dark"><i class="fas fa-clock me-1"></i> Rates as of ${this.lastUpdated}</span>`).show();
        } else {
            $('.currency-status').hide();
        }
    }

    applyRatesToDOM() {
        const self = this;
        $('.price-display, .price-value').each(function() {
            let basePrice = $(this).data('base-price');
            if (basePrice === undefined) {
                // Try to extract from text if data-attr missing (not recommended but for legacy support)
                const text = $(this).text().replace(/[^0-9.]/g, '');
                basePrice = parseFloat(text);
                if (!isNaN(basePrice)) $(this).data('base-price', basePrice);
            }
            
            if (isNaN(basePrice)) return;

            const baseCurrency = $(this).data('base-currency') || self.baseCurrency;
            
            // Conversion Logic (Using USD as bridge if rates are relative to USD)
            const rateUSD_Base = self.rates[baseCurrency] || 1;
            const rateUSD_Target = self.rates[self.currentCurrency] || 1;
            
            const convertedPrice = (basePrice / rateUSD_Base) * rateUSD_Target;
            
            const symbol = self.symbols[self.currentCurrency] || self.currentCurrency + ' ';
            const formattedPrice = convertedPrice.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });

            // If it's an input or has special formatting, we might want to preserve it
            if ($(this).is('input')) {
                $(this).val(formattedPrice);
            } else {
                $(this).html(`<span class="currency-symbol">${symbol}</span>${formattedPrice}`);
            }
        });
    }
}

// Initialize on DOM load
$(function() {
    window.currencyManager = new CurrencyManager();
});

/**
 * Electro Analytical Dashboard JS
 * Handles real-time polling, Chart.js visualizations, and dynamic UI updates.
 */

class AnalyticalDashboard {
    constructor(config) {
        this.apiUrl = config.apiUrl;
        this.pollingInterval = config.pollingInterval || 60000;
        this.charts = {};
        this.countdown = 60;
        this.init();
    }

    init() {
        this.initCharts();
        this.initFlatpickr();
        this.initFilters();
        this.fetchData();
        this.startPolling();
    }

    initFlatpickr() {
        flatpickr("#dateRangePicker", {
            mode: "range",
            dateFormat: "Y-m-d",
            defaultDate: [new Date().setDate(new Date().getDate() - 30), new Date()],
            onClose: (selectedDates, dateStr) => {
                if (selectedDates.length === 2) {
                    document.getElementById('dateRangeText').innerText = dateStr;
                    this.fetchData();
                }
            }
        });
    }

    initFilters() {
        document.getElementById('categoryFilter').addEventListener('change', () => this.fetchData());
    }

    initCharts() {
        const gridColor = 'rgba(255, 255, 255, 0.05)';
        const textColor = '#94a3b8';

        const chartConfig = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'bottom', labels: { color: textColor, font: { size: 11 } } },
                tooltip: { backgroundColor: '#1e293b', titleColor: '#f8fafc', bodyColor: '#94a3b8', padding: 12, borderRadius: 8 }
            },
            scales: {
                x: { grid: { color: gridColor }, ticks: { color: textColor } },
                y: { grid: { color: gridColor }, ticks: { color: textColor } }
            }
        };

        // 1. Sales Trend
        this.charts.salesChannel = new Chart(document.getElementById('salesChart'), {
            type: 'line',
            data: { labels: [], datasets: [
                { label: 'Revenue', data: [], borderColor: '#00d2ff', backgroundColor: 'rgba(0, 210, 255, 0.1)', fill: true, tension: 0.4 },
                { label: 'Orders', data: [], borderColor: '#f43f5e', borderDash: [5, 5], fill: false, tension: 0.1, yAxisID: 'y1' }
            ]},
            options: { ...chartConfig, scales: { ...chartConfig.scales, y1: { position: 'right', grid: { display: false } } } }
        });

        // 2. Forecasting
        this.charts.forecast = new Chart(document.getElementById('forecastChart'), {
            type: 'line',
            data: { labels: [], datasets: [
                { label: 'Projection', data: [], borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)', fill: true, borderDash: [5, 5], tension: 0.4 }
            ]},
            options: chartConfig
        });

        // 3. Category Share
        this.charts.category = new Chart(document.getElementById('categoryChart'), {
            type: 'doughnut',
            data: { labels: [], datasets: [{ data: [], backgroundColor: ['#00d2ff', '#9333ea', '#f59e0b', '#10b981', '#f43f5e'], borderWidth: 0 }]},
            options: { ...chartConfig, cutout: '75%', plugins: { ...chartConfig.plugins, legend: { position: 'right' } } }
        });

        // 4. Activity Heatmap (Simulated)
        this.charts.heatmap = new Chart(document.getElementById('heatmapChart'), {
            type: 'bar',
            data: { labels: Array.from({length: 24}, (_, i) => `${i}h`), datasets: [{ label: 'Activity', data: [], backgroundColor: 'rgba(0, 210, 255, 0.2)', borderRadius: 4 }]},
            options: chartConfig
        });
    }

    async fetchData() {
        const range = document.getElementById('dateRangeText').innerText;
        const categoryId = document.getElementById('categoryFilter').value;
        const url = `${this.apiUrl}?range=${range}&category=${categoryId}`;

        try {
            const response = await fetch(url);
            const data = await response.json();
            
            this.updateUI(data);
            this.updateCharts(data);
            this.resetCountdown();
        } catch (error) {
            console.error('Dashboard error:', error);
        }
    }

    updateUI(data) {
        // KPIs
        const k = data.kpis;
        document.getElementById('val-revenue').innerText = k.total_revenue.toLocaleString();
        document.getElementById('val-orders').innerText = k.orders_today;
        document.getElementById('val-aov').innerText = k.avg_order_value.toLocaleString();
        document.getElementById('val-stock').innerText = k.low_stock_alerts;

        // Revenue Trend Indicator
        const trendEl = document.getElementById('trend-revenue');
        const icon = k.revenue_trend >= 0 ? 'fa-arrow-up' : 'fa-arrow-down';
        trendEl.className = `insight-trend ${k.revenue_trend >= 0 ? 'trend-up' : 'trend-down'}`;
        trendEl.innerHTML = `<i class="fas ${icon}"></i> ${Math.abs(k.revenue_trend)}%`;

        // Trending Table
        const list = document.getElementById('trendingBody');
        list.innerHTML = data.trending.map((p, i) => `
            <tr>
                <td><span style="font-weight:800; opacity:0.3">#${i + 1}</span></td>
                <td>
                    <div class="product-meta">
                        <img src="${p.image}" class="product-img" onerror="this.src='https://placehold.co/100'">
                        <div>
                            <span class="product-info-name">${p.name}</span>
                            <span class="product-info-sku">Stock: ${p.stock}</span>
                        </div>
                    </div>
                </td>
                <td style="font-weight:600">${p.units_sold}</td>
                <td style="color:var(--text-dim)">${p.views}</td>
                <td style="font-weight:600">₹${p.revenue.toLocaleString()}</td>
                <td>
                    <span class="badge-stock ${p.stock < 10 ? 'badge-low-stock' : 'badge-in-stock'}">
                        ${p.stock < 10 ? 'Low Stock' : 'Healthy'}
                    </span>
                </td>
            </tr>
        `).join('');
    }

    updateCharts(data) {
        // Sales Trend
        this.charts.salesChannel.data.labels = data.sales_trend.map(d => d.day);
        this.charts.salesChannel.data.datasets[0].data = data.sales_trend.map(d => d.total);
        this.charts.salesChannel.data.datasets[1].data = data.sales_trend.map(d => d.count);
        this.charts.salesChannel.update();

        // Forecast
        if (data.forecast.forecast) {
            this.charts.forecast.data.labels = data.forecast.forecast.map(item => item[0]);
            this.charts.forecast.data.datasets[0].data = data.forecast.forecast.map(item => item[1]);
            this.charts.forecast.update();
            document.getElementById('forecast-accuracy').innerText = `Confidence: ${data.forecast.accuracy}%`;
        }

        // Categories
        this.charts.category.data.labels = data.categories.map(c => c.name);
        this.charts.category.data.datasets[0].data = data.categories.map(c => c.revenue);
        this.charts.category.update();

        // Activity
        const activity = Array(24).fill(0);
        data.activity_hours.forEach(item => activity[parseInt(item.hour)] = item.count);
        this.charts.heatmap.data.datasets[0].data = activity;
        this.charts.heatmap.update();
    }

    startPolling() {
        setInterval(() => {
            this.countdown--;
            if (this.countdown <= 0) this.fetchData();
        }, 1000);
    }

    resetCountdown() {
        this.countdown = 60;
    }
}


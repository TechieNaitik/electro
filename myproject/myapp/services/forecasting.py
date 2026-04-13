import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import timedelta, datetime
from django.db.models import Sum, Count
from django.db.models.functions import TruncDay
from ..models import OrderItem, Product, Order

class ForecastingService:
    @staticmethod
    def predict_sales(product_id=None, category_id=None, days_ahead=30):
        """
        Predicts sales volume for a product or category using Linear Regression.
        """
        # Get historical sales data
        queryset = OrderItem.objects.all()
        if product_id:
            queryset = queryset.filter(variant__product_id=product_id)
        if category_id:
            queryset = queryset.filter(variant__product__category_id=category_id)
        
        # Aggregate by day
        historical_data = queryset.annotate(
            day=TruncDay('order__created_at')
        ).values('day').annotate(
            total_sales=Sum('quantity')
        ).order_by('day')

        forecast_dates = [
            (datetime.now() + timedelta(days=i+1)).strftime('%Y-%m-%d')
            for i in range(days_ahead)
        ]

        if not historical_data:
            return {
                'forecast': list(zip(forecast_dates, [0] * days_ahead)),
                'accuracy': 0,
                'status': 'No historical data available'
            }

        # Prepare data for Linear Regression
        # X: days since first sale, y: total sales
        first_day = historical_data[0]['day']
        X = []
        y = []
        for entry in historical_data:
            days_since_start = (entry['day'] - first_day).days
            X.append([days_since_start])
            y.append(entry['total_sales'])

        X = np.array(X)
        y = np.array(y)

        if len(X) < 2:
            # Fallback for insufficient data
            avg_sales = np.mean(y) if len(y) > 0 else 0
            return {
                'forecast': list(zip(forecast_dates, [avg_sales] * days_ahead)),
                'accuracy': 0,
                'status': 'Insufficient data for regression, using average'
            }

        model = LinearRegression()
        model.fit(X, y)

        # Predict future sales
        last_day_since_start = X[-1][0]
        future_X = np.array([[last_day_since_start + i + 1] for i in range(days_ahead)])
        predictions = model.predict(future_X)
        
        # Ensure non-negative predictions
        predictions = np.clip(predictions, 0, None)

        # Calculate accuracy score (R^2 or MAPE)
        score = model.score(X, y)

        return {
            'forecast': list(zip(forecast_dates, predictions.tolist())),
            'accuracy': round(score * 100, 2),
            'status': 'Success'
        }

    @staticmethod
    def analyze_low_stock(product):
        """
        Analyzes if a product is at risk of stockout based on forecast.
        """
        # Get 30-day forecast
        forecast_data = ForecastingService.predict_sales(product_id=product.id, days_ahead=30)
        total_predicted = sum([val for date, val in forecast_data['forecast']])
        
        # Use total_stock property for Product level aggregate
        stock = getattr(product, 'total_stock', getattr(product, 'stock_quantity', 0))
        
        if total_predicted > stock:
            days_until_stockout = 0
            cumulative = 0
            for i, (date, val) in enumerate(forecast_data['forecast']):
                cumulative += val
                if cumulative >= stock:
                    days_until_stockout = i + 1
                    break
            return {
                'at_risk': True,
                'days_left': days_until_stockout,
                'predicted_demand_30d': total_predicted
            }
        
        return {
            'at_risk': False,
            'days_left': 30, # More than 30
            'predicted_demand_30d': total_predicted
        }

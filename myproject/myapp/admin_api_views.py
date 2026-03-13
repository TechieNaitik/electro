from django.http import JsonResponse
from django.db.models import Sum, Count, F, Q, Avg
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.cache import cache
from .models import Order, OrderItem, Product, Category, ProductView
from .services.forecasting import ForecastingService
from functools import wraps
import re

def staff_required_json(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('_site_admin_user_id'):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@staff_required_json
def dashboard_stats_api(request):
    # Cache key based on parameters
    time_range = request.GET.get('range', '30d') # today, 7d, 30d, custom
    category_id = request.GET.get('category')
    
    # Safely generate cache key for memcached (no spaces)
    safe_time_range = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(time_range))
    safe_category = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(category_id))
    cache_key = f'dashboard_stats_{safe_time_range}_{safe_category}'
    data = cache.get(cache_key)
    if data:
        return JsonResponse(data)

    # Determine date threshold
    now = timezone.now()
    if time_range == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == '7d':
        start_date = now - timedelta(days=7)
    elif time_range == '30d':
        start_date = now - timedelta(days=30)
    elif time_range == 'custom':
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        try:
            start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
            # End date handling omitted for brevity, usually end of day
        except:
            start_date = now - timedelta(days=30)
    else:
        start_date = now - timedelta(days=30)

    # Calculate previous period for trend analysis
    period_delta = now - start_date
    prev_start_date = start_date - period_delta
    prev_end_date = start_date

    # 1. KPI Summary
    orders_query = Order.objects.filter(created_at__date=now.date())
    
    if category_id:
        orders_query = orders_query.filter(items__product__category_id=category_id).distinct()
        
        rev_agg = OrderItem.objects.filter(
            order__created_at__gte=start_date,
            product__category_id=category_id
        ).aggregate(total_rev=Sum(F('quantity') * F('price')))
        total_revenue = rev_agg['total_rev'] or 0
        
        prev_rev_agg = OrderItem.objects.filter(
            order__created_at__gte=prev_start_date,
            order__created_at__lt=prev_end_date,
            product__category_id=category_id
        ).aggregate(total_rev=Sum(F('quantity') * F('price')))
        prev_revenue = prev_rev_agg['total_rev'] or 0
        
        total_orders_for_cat = Order.objects.filter(created_at__gte=start_date, items__product__category_id=category_id).distinct().count()
        avg_order_value = (total_revenue / total_orders_for_cat) if total_orders_for_cat > 0 else 0
        
    else:
        revenue_query = Order.objects.filter(created_at__gte=start_date)
        prev_revenue_query = Order.objects.filter(created_at__gte=prev_start_date, created_at__lt=prev_end_date)
        
        revenue_data = revenue_query.aggregate(
            total_rev=Sum('total_amount'),
            avg_order=Avg('total_amount')
        )
        total_revenue = revenue_data['total_rev'] or 0
        avg_order_value = revenue_data['avg_order'] or 0
        
        prev_revenue = prev_revenue_query.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    orders_today = orders_query.count()
    rev_trend = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0

    low_stock_count = Product.objects.filter(stock_quantity__lt=F('reorder_threshold'))
    if category_id:
        low_stock_count = low_stock_count.filter(category_id=category_id)
    low_stock_count = low_stock_count.count()

    # 2. Trending Products
    product_qs = Product.objects.all()
    if category_id:
        product_qs = product_qs.filter(category_id=category_id)

    trending_products = product_qs.annotate(
        units_sold=Sum('orderitem__quantity', filter=Q(orderitem__order__created_at__gte=start_date)),
        period_views=Count('views', filter=Q(views__timestamp__gte=start_date)),
        revenue=Sum(F('orderitem__quantity') * F('orderitem__price'), filter=Q(orderitem__order__created_at__gte=start_date))
    ).order_by('-units_sold')[:10]

    # Previous period metrics for trend arrows
    prev_metrics = Product.objects.filter(id__in=[p.id for p in trending_products]).annotate(
        prev_units=Sum('orderitem__quantity', filter=Q(orderitem__order__created_at__gte=prev_start_date, orderitem__order__created_at__lt=prev_end_date))
    ).values('id', 'prev_units')
    
    prev_map = {m['id']: (m['prev_units'] or 0) for m in prev_metrics}

    trending_list = []
    for p in trending_products:
        curr_units = p.units_sold or 0
        prev_units = prev_map.get(p.id, 0)
        trend = 'up' if curr_units >= prev_units else 'down'
        
        trending_list.append({
            'id': p.id,
            'name': p.name,
            'image': p.image.url if p.image else '',
            'units_sold': curr_units,
            'views': p.period_views or 0,
            'revenue': p.revenue or 0,
            'stock': p.stock_quantity,
            'trend': trend
        })

    kpi_data = {
        'total_revenue': total_revenue,
        'revenue_trend': round(rev_trend, 1),
        'orders_today': orders_today,
        'avg_order_value': round(avg_order_value, 2),
        'low_stock_alerts': low_stock_count
    }

    # 3. Demand Analysis (Sales Chart)
    if category_id:
        sales_trend_qs = OrderItem.objects.filter(
            order__created_at__gte=start_date,
            product__category_id=category_id
        ).annotate(
            day=TruncDay('order__created_at')
        ).values('day').annotate(
            total=Sum(F('quantity') * F('price')),
            count=Count('order__id', distinct=True)
        ).order_by('day')
    else:
        sales_trend_qs = Order.objects.filter(created_at__gte=start_date).annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('day')
        
    # Pad missing dates with zero values so Chart.js renders a continuous timeline
    sales_dict = {item['day'].strftime('%Y-%m-%d'): item for item in sales_trend_qs if item['day']}
    sales_trend = []
    
    current_date = start_date.date()
    end_date = now.date()
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        if date_str in sales_dict:
            sales_trend.append({
                'day': date_str,
                'total': sales_dict[date_str]['total'] or 0,
                'count': sales_dict[date_str]['count'] or 0
            })
        else:
            sales_trend.append({
                'day': date_str,
                'total': 0,
                'count': 0
            })
        current_date += timedelta(days=1)

    # 4. Category Distribution
    category_dist = Category.objects.annotate(
        revenue=Sum(F('product__orderitem__quantity') * F('product__orderitem__price'), 
                    filter=Q(product__orderitem__order__created_at__gte=start_date))
    ).values('name', 'revenue').order_by('-revenue')[:5]

    # 5. Order Activity by Hour
    activity_hours = Order.objects.filter(created_at__gte=start_date).extra(
        select={'hour': "strftime('%%H', created_at)"}
    ).values('hour').annotate(count=Count('id')).order_by('hour')
    
    # 6. Forecasting (Example for top product)
    top_p = trending_products.first()
    
    forecast_dates_empty = [
        (datetime.now() + timedelta(days=i+1)).strftime('%Y-%m-%d')
        for i in range(7)
    ]
    forecast_data = {
        'forecast': list(zip(forecast_dates_empty, [0] * 7)),
        'accuracy': 0,
        'status': 'No trending product'
    }
    
    if top_p:
        forecast_data = ForecastingService.predict_sales(product_id=top_p.id, days_ahead=7)

    data = {
        'kpis': kpi_data,
        'trending': trending_list,
        'sales_trend': list(sales_trend),
        'categories': list(category_dist),
        'activity_hours': list(activity_hours),
        'forecast': forecast_data
    }

    # Cache for 60 seconds (as requested for polling interval)
    cache.set(cache_key, data, 60)
    return JsonResponse(data)

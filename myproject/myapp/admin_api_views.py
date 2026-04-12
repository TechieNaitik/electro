from django.http import JsonResponse
from django.db.models import Sum, Count, F, Q, Avg
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.cache import cache
from .models import Order, OrderItem, Product, Category, ProductView, Brand, ProductVariant
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
    brand_id = request.GET.get('brand')
    
    # Safely generate cache key for memcached (no spaces)
    safe_time_range = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(time_range))
    safe_category = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(category_id))
    safe_brand = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(brand_id))
    cache_key = f'dashboard_stats_{safe_time_range}_{safe_category}_{safe_brand}'
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
        try:
            start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
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
    rev_items_query = OrderItem.objects.filter(order__created_at__gte=start_date)
    prev_rev_items_query = OrderItem.objects.filter(order__created_at__gte=prev_start_date, order__created_at__lt=prev_end_date)
    
    if category_id:
        orders_query = orders_query.filter(items__product__category_id=category_id).distinct()
        rev_items_query = rev_items_query.filter(product__category_id=category_id)
        prev_rev_items_query = prev_rev_items_query.filter(product__category_id=category_id)
        
    if brand_id:
        orders_query = orders_query.filter(items__product__brand_id=brand_id).distinct()
        rev_items_query = rev_items_query.filter(product__brand_id=brand_id)
        prev_rev_items_query = prev_rev_items_query.filter(product__brand_id=brand_id)

    # Calculate Current Revenue
    total_revenue = rev_items_query.aggregate(total_rev=Sum(F('quantity') * F('price')))['total_rev'] or 0
    
    # Calculate Previous Revenue
    prev_revenue = prev_rev_items_query.aggregate(total_rev=Sum(F('quantity') * F('price')))['total_rev'] or 0
    
    # Calculate Orders & AOV
    total_orders_in_period = orders_query.filter(created_at__gte=start_date).distinct().count()
    if not (category_id or brand_id):
        # Using Order table directly is more accurate for whole store
        revenue_data = Order.objects.filter(created_at__gte=start_date).aggregate(
            total_rev=Sum('total_amount'),
            avg_order=Avg('total_amount')
        )
        total_revenue = revenue_data['total_rev'] or 0
        avg_order_value = revenue_data['avg_order'] or 0
        
        prev_revenue = Order.objects.filter(created_at__gte=prev_start_date, created_at__lt=prev_end_date).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    else:
        avg_order_value = (total_revenue / total_orders_in_period) if total_orders_in_period > 0 else 0

    orders_today = orders_query.count()
    rev_trend = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0

    from .models import ProductVariant
    low_stock_count_qs = ProductVariant.objects.filter(stock_quantity__lt=F('reorder_threshold'))
    if category_id: low_stock_count_qs = low_stock_count_qs.filter(product__category_id=category_id)
    if brand_id: low_stock_count_qs = low_stock_count_qs.filter(product__brand_id=brand_id)
    low_stock_count = low_stock_count_qs.count()

    # 2. Trending Products
    product_qs = Product.objects.all()
    if category_id: product_qs = product_qs.filter(category_id=category_id)
    if brand_id: product_qs = product_qs.filter(brand_id=brand_id)

    trending_products = product_qs.select_related('brand').annotate(
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
            'name': p.full_name,
            'image': p.featured_image_url,
            'units_sold': curr_units,
            'views': p.period_views or 0,
            'revenue': p.revenue or 0,
            'stock': p.total_stock,
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
    if category_id or brand_id:
        sales_items = OrderItem.objects.filter(order__created_at__gte=start_date)
        if category_id: sales_items = sales_items.filter(product__category_id=category_id)
        if brand_id: sales_items = sales_items.filter(product__brand_id=brand_id)
        
        sales_trend_qs = sales_items.annotate(
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
        
    # Pad missing dates with zero values
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

    # 4. Distributions
    category_dist = Category.objects.annotate(
        revenue=Sum(F('product__orderitem__quantity') * F('product__orderitem__price'), 
                    filter=Q(product__orderitem__order__created_at__gte=start_date))
    ).values('name', 'revenue').order_by('-revenue')[:5]

    brand_dist = Brand.objects.annotate(
        revenue=Sum(F('products__orderitem__quantity') * F('products__orderitem__price'), 
                    filter=Q(products__orderitem__order__created_at__gte=start_date))
    ).values('name', 'revenue').order_by('-revenue')[:5]

    # 5. Order Activity by Hour
    activity_hours = Order.objects.filter(created_at__gte=start_date).extra(
        select={'hour': "strftime('%%H', created_at)"}
    ).values('hour').annotate(count=Count('id')).order_by('hour')
    
    # 6. Forecasting
    top_p = trending_products.first()
    forecast_data = {
        'forecast': list(zip([ (now + timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(7) ], [0] * 7)),
        'accuracy': 0,
        'status': 'No data'
    }
    if top_p:
        forecast_data = ForecastingService.predict_sales(product_id=top_p.id, days_ahead=7)

    data = {
        'kpis': kpi_data,
        'trending': trending_list,
        'sales_trend': list(sales_trend),
        'categories': list(category_dist),
        'brands': list(brand_dist),
        'activity_hours': list(activity_hours),
        'forecast': forecast_data
    }

    cache.set(cache_key, data, 60)
    return JsonResponse(data)

from django.core.paginator import Paginator

def get_paginated_data(request, queryset, per_page=12):
    """
    Helper function to paginate any queryset.
    Returns the page object for the current page.
    """
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)

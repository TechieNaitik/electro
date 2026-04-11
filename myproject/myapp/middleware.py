import traceback
import sys
import os
import linecache
import logging
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseServerError

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware:
    """
    Middleware to catch all unhandled exceptions and route them to a 
    dedicated error page with detailed context.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            return self.process_exception(request, e)

    def process_exception(self, request, exception):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb = traceback.extract_tb(exc_traceback)
        
        # Get location details
        if tb:
            # Filter traceback to find the last app-related file if possible, 
            # or just take the very last one.
            last_tb = tb[-1]
            file_path = last_tb.filename
            line_no = last_tb.lineno
            func_name = last_tb.name
        else:
            file_path = "Unknown"
            line_no = 0
            func_name = "Unknown"

        # Code snippet (±5 lines)
        code_snippet = []
        if os.path.exists(file_path):
            start = max(1, line_no - 5)
            end = line_no + 5
            linecache.checkcache(file_path)
            for i in range(start, end + 1):
                line = linecache.getline(file_path, i)
                if line is not None:
                    code_snippet.append({
                        'line_no': i,
                        'content': line.rstrip('\n\r'),
                        'is_error_line': i == line_no
                    })
        
        stack_trace = traceback.format_exc()
        
        exc_name = exc_type.__name__ if exc_type else "Exception"
        # Log server-side in all environments (as requested)
        logger.error(f"Unhandled Exception ({exc_name}): {exception}\nPath: {request.path}\n{stack_trace}")

        context = {
            'error_type': exc_type.__name__ if exc_type else "Error",
            'error_message': str(exception),
            'file_path': file_path,
            'line_number': line_no,
            'function_name': func_name,
            'stack_trace': stack_trace,
            'code_snippet': code_snippet,
            'debug': settings.DEBUG,
            'status_code': 500,
            'request_path': request.path,
        }

        try:
            # Avoid infinite loops by not using a base template that might fail if 
            # request context is broken or if there's a problem in index.html
            return render(request, 'error.html', context, status=500)
        except Exception as render_err:
            logger.critical(f"Error rendering error template: {render_err}", exc_info=True)
            # Minimal fallback
            return HttpResponseServerError(
                f"<h1>Internal Server Error</h1><p>{exception}</p><hr><p>Error rendering error page: {render_err}</p>",
                content_type="text/html"
            )

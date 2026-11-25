"""
Global project views and custom HTTP error handlers (404, 403, 500) for Antique Hub.
"""

from django.shortcuts import render


def error_404(request, exception=None):
    """Custom 404 Page Not Found handler."""
    return render(request, '404.html', status=404)


def error_403(request, exception=None):
    """Custom 403 Forbidden / Permission Denied handler."""
    return render(request, '403.html', status=403)


def error_500(request):
    """Custom 500 Internal Server Error handler."""
    return render(request, '500.html', status=500)

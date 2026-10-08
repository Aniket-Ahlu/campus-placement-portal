from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render


def role_required(allowed_roles):
    """
    Decorator to restrict view access to specific roles.
    If unauthenticated, redirects to login.
    If authenticated with wrong role, raises 403 (PermissionDenied) or renders 403.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.conf import settings
                from django.shortcuts import redirect
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")

            # Superusers always pass
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Check role
            if request.user.role not in allowed_roles:
                return render(request, '403.html', {
                    'message': f"Access forbidden. This area is reserved for {', '.join(allowed_roles)} users."
                }, status=403)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def student_required(view_func):
    return role_required(['STUDENT'])(view_func)


def recruiter_required(view_func):
    return role_required(['RECRUITER'])(view_func)


def admin_required(view_func):
    return role_required(['ADMIN'])(view_func)

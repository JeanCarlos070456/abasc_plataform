from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from .models import User

def role_required(minimum_role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not request.user.has_role(minimum_role):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator

associate_required = role_required(User.Role.ASSOCIATE)
executive_required = role_required(User.Role.EXECUTIVE)
president_required = role_required(User.Role.PRESIDENT)

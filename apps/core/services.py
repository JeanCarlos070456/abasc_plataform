from .models import AuditLog

def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

def log_action(request, action, description, object_type='', object_id=''):
    AuditLog.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        action=action,
        description=description[:255],
        object_type=object_type[:80],
        object_id=str(object_id)[:80],
        ip_address=client_ip(request),
    )

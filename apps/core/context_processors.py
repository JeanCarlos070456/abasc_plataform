from django.conf import settings
from .models import SiteConfiguration

def site_context(request):
    try:
        config = SiteConfiguration.current()
    except Exception:
        config = None
    return {
        'site_config': config,
        'abasc_contact_email': settings.ABASC_CONTACT_EMAIL,
        'abasc_site_name': settings.ABASC_SITE_NAME,
        'abasc_full_name': settings.ABASC_FULL_NAME,
    }

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView


urlpatterns = [
    path("admin/", admin.site.urls),

    # Atalho para a página de login oficial do sistema
    path(
        "login/",
        RedirectView.as_view(
            url="/conta/login/",
            permanent=False,
        ),
        name="login_alias",
    ),

    path("conta/", include("apps.accounts.urls")),
    path("noticias/", include("apps.news.urls")),
    path("associado/", include("apps.associates.urls")),
    path("painel/", include("apps.dashboards.urls")),

    # Deve permanecer por último
    path("", include("apps.core.urls")),
]


handler403 = "apps.core.views.error_403"
handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class LegacyOnboardingMiddleware:
    """
    Impede que um associado migrado e autenticado acesse áreas internas
    antes de concluir o onboarding obrigatório.

    O middleware não interfere em usuários anônimos e libera somente as
    rotas necessárias para concluir/sair do fluxo.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)

        if (
            user is not None
            and user.is_authenticated
            and getattr(user, "needs_onboarding", False)
            and not self._is_allowed_path(request.path)
        ):
            return redirect("accounts:onboarding")

        return self.get_response(request)

    @staticmethod
    def _is_allowed_path(path):
        allowed_paths = {
            reverse("accounts:onboarding"),
            reverse("accounts:logout"),
            reverse("accounts:create_password"),
        }

        if path in allowed_paths:
            return True

        static_url = getattr(settings, "STATIC_URL", "/static/")
        media_url = getattr(settings, "MEDIA_URL", "/media/")

        if static_url and path.startswith(static_url):
            return True

        if media_url and path.startswith(media_url):
            return True

        return False

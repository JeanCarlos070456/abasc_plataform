import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from apps.core.models import AuditLog
from apps.core.services import log_action
from apps.core.storage import delete_avatar, upload_avatar
from apps.associates.services import (
    MembershipProcessingError,
    resend_member_access,
)

from .forms import (
    AvatarForm,
    FirstAccessForm,
    LoginForm,
    OnboardingAvatarForm,
    OnboardingForm,
    ProfileForm,
)
from .models import User
from .services import (
    SupabaseAuthError,
    SupabaseAuthService,
    sync_supabase_user,
)


logger = logging.getLogger(__name__)



@require_http_methods(['GET'])
def create_password(request):
    """
    Exibe a página que consome a sessão temporária do convite/recuperação
    no navegador e permite definir a senha diretamente no Supabase Auth.

    Somente a chave pública é enviada ao template. A chave secreta nunca
    sai do backend.
    """
    return render(
        request,
        'accounts/create_password.html',
        {
            'supabase_config': {
                'url': settings.SUPABASE_URL,
                'publishableKey': settings.SUPABASE_ANON_KEY,
                'loginUrl': request.build_absolute_uri(
                    '/conta/entrar/'
                ),
                'minimumLength': int(
                    getattr(settings, 'ABASC_PASSWORD_MIN_LENGTH', 8)
                ),
            },
        },
    )


@require_http_methods(["GET", "POST"])
def first_access(request):
    """
    Porta de entrada dos associados migrados da base histórica.

    O formulário confirma e-mail + CPF no cadastro Django. A autenticação
    continua sendo feita pelo Supabase. A resposta é genérica para não
    revelar se um cadastro existe ou não.
    """
    if request.user.is_authenticated:
        return redirect("accounts:post_login")

    form = FirstAccessForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        cpf = form.cleaned_data["cpf"]

        user = User.objects.filter(
            email__iexact=email,
            cpf=cpf,
            legacy_imported=True,
            is_active=True,
        ).first()

        if user is not None:
            try:
                resend_member_access(user)
            except MembershipProcessingError:
                logger.exception(
                    "Falha ao processar primeiro acesso do usuário %s.",
                    user.pk,
                )
            except Exception:
                logger.exception(
                    "Erro inesperado no primeiro acesso do usuário %s.",
                    user.pk,
                )

        messages.success(
            request,
            "Se os dados informados corresponderem a um cadastro habilitado, "
            "você receberá no e-mail um link seguro para criar ou redefinir "
            "sua senha.",
        )
        return redirect("accounts:first_access")

    return render(
        request,
        "accounts/first_access.html",
        {"form": form},
    )

def _local_sign_in(email, password):
    if not settings.ENABLE_LOCAL_AUTH:
        return None

    try:
        user = User.objects.get(email__iexact=email, is_active=True)
    except User.DoesNotExist:
        return None

    return user if user.check_password(password) else None


def _validation_message(exc: ValidationError) -> str:
    messages_list = getattr(exc, 'messages', None)
    if messages_list:
        return messages_list[0]
    return str(exc)


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:post_login')

    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].strip().lower()
        password = form.cleaned_data['password']
        user = None

        if SupabaseAuthService.configured():
            try:
                session = SupabaseAuthService.sign_in(email, password)
                user = sync_supabase_user(session)
                request.session['supabase_access_token'] = (
                    session.access_token
                )
                request.session['supabase_refresh_token'] = (
                    session.refresh_token
                )
            except SupabaseAuthError as exc:
                if settings.ENABLE_LOCAL_AUTH:
                    user = _local_sign_in(email, password)
                if user is None:
                    form.add_error(None, str(exc))
        else:
            user = _local_sign_in(email, password)
            if user is None:
                form.add_error(
                    None,
                    'E-mail ou senha inválidos. Configure o Supabase '
                    'ou use uma conta local de desenvolvimento.',
                )

        if user is not None:
            login(
                request,
                user,
                backend='django.contrib.auth.backends.ModelBackend',
            )
            log_action(
                request,
                AuditLog.Action.LOGIN,
                f'Login de {user.email}',
                'User',
                user.pk,
            )
            messages.success(
                request,
                f'Bem-vindo(a), {user.display_name}.',
            )

            if user.needs_onboarding:
                return redirect('accounts:onboarding')

            next_url = (
                request.POST.get('next')
                or request.GET.get('next')
            )
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

            return redirect('accounts:post_login')

    return render(
        request,
        'accounts/login.html',
        {'form': form, 'next': request.GET.get('next', '')},
    )


@login_required
def post_login(request):
    if request.user.needs_onboarding:
        return redirect('accounts:onboarding')
    if request.user.is_president:
        return redirect('dashboards:president')
    if request.user.can_manage_content:
        return redirect('dashboards:executive')
    return redirect('associates:dashboard')


@require_POST
def logout_view(request):
    token = request.session.get('supabase_access_token', '')

    if request.user.is_authenticated:
        log_action(
            request,
            AuditLog.Action.LOGOUT,
            f'Logout de {request.user.email}',
            'User',
            request.user.pk,
        )

    SupabaseAuthService.sign_out(token)
    logout(request)
    messages.info(request, 'Sessão encerrada com segurança.')
    return redirect('core:home')



@login_required
@require_http_methods(["GET", "POST"])
def onboarding(request):
    """
    Etapa obrigatória após a criação da senha no primeiro acesso.
    O associado revisa seus dados e adiciona a foto de perfil.
    """
    if not request.user.needs_onboarding:
        return redirect("accounts:post_login")

    profile_form = OnboardingForm(
        request.POST or None,
        instance=request.user,
        prefix="profile",
    )
    avatar_form = OnboardingAvatarForm(
        request.POST or None,
        request.FILES or None,
        user=request.user,
        prefix="avatar",
    )

    if (
        request.method == "POST"
        and profile_form.is_valid()
        and avatar_form.is_valid()
    ):
        new_avatar = avatar_form.cleaned_data.get("avatar")
        old_path = request.user.avatar_path
        new_path = ""

        try:
            if new_avatar:
                new_path = upload_avatar(
                    new_avatar,
                    user_id=request.user.pk,
                )

            with transaction.atomic():
                user = profile_form.save(commit=False)

                if new_path:
                    user.avatar_path = new_path
                    user.avatar_url = ""

                user.onboarding_completed = True
                user.migration_status = User.MigrationStatus.READY
                user.save()

                log_action(
                    request,
                    AuditLog.Action.UPDATE,
                    "Primeiro acesso concluído e dados cadastrais validados",
                    "User",
                    user.pk,
                )

                if old_path and new_path and old_path != new_path:
                    transaction.on_commit(
                        lambda path=old_path: delete_avatar(path)
                    )

        except ValidationError as exc:
            if new_path:
                delete_avatar(new_path)
            avatar_form.add_error(
                "avatar",
                _validation_message(exc),
            )
        except ImproperlyConfigured:
            if new_path:
                delete_avatar(new_path)
            avatar_form.add_error(
                None,
                "O armazenamento de avatares não está configurado.",
            )
        except Exception:
            if new_path:
                delete_avatar(new_path)
            logger.exception(
                "Falha ao concluir onboarding do usuário %s.",
                request.user.pk,
            )
            profile_form.add_error(
                None,
                "Não foi possível concluir seu primeiro acesso. "
                "Tente novamente.",
            )
        else:
            messages.success(
                request,
                "Cadastro atualizado. Seu primeiro acesso foi concluído.",
            )
            return redirect("accounts:post_login")

    return render(
        request,
        "accounts/onboarding.html",
        {
            "form": profile_form,
            "avatar_form": avatar_form,
        },
    )

@login_required
@require_http_methods(['GET', 'POST'])
def profile(request):
    if request.user.needs_onboarding:
        return redirect("accounts:onboarding")

    profile_form = ProfileForm(
        instance=request.user,
        prefix='profile',
    )
    avatar_form = AvatarForm(prefix='avatar')
    can_update_avatar = request.user.can_update_avatar

    if request.method == 'POST':
        action = request.POST.get('action', 'profile')

        if action == 'avatar':
            avatar_form = AvatarForm(
                request.POST,
                request.FILES,
                prefix='avatar',
            )

            if not can_update_avatar:
                messages.error(
                    request,
                    'A foto de perfil fica disponível somente para '
                    'associados aprovados e ativos.',
                )

            elif avatar_form.is_valid():
                new_avatar = avatar_form.cleaned_data.get('avatar')
                remove_avatar = avatar_form.cleaned_data.get(
                    'remove_avatar'
                )
                old_path = request.user.avatar_path

                if remove_avatar:
                    if not old_path and not request.user.avatar_url:
                        avatar_form.add_error(
                            None,
                            'Você ainda não possui uma foto para remover.',
                        )
                    else:
                        with transaction.atomic():
                            request.user.avatar_path = ''
                            request.user.avatar_url = ''
                            request.user.save(update_fields=[
                                'avatar_path',
                                'avatar_url',
                                'profile_updated_at',
                            ])
                            log_action(
                                request,
                                AuditLog.Action.UPDATE,
                                'Foto de perfil removida',
                                'User',
                                request.user.pk,
                            )

                            if old_path:
                                transaction.on_commit(
                                    lambda path=old_path: delete_avatar(path)
                                )

                        messages.success(
                            request,
                            'Sua foto de perfil foi removida.',
                        )
                        return redirect('accounts:profile')

                elif new_avatar:
                    new_path = ''

                    try:
                        new_path = upload_avatar(
                            new_avatar,
                            user_id=request.user.pk,
                        )

                        with transaction.atomic():
                            request.user.avatar_path = new_path
                            request.user.avatar_url = ''
                            request.user.save(update_fields=[
                                'avatar_path',
                                'avatar_url',
                                'profile_updated_at',
                            ])
                            log_action(
                                request,
                                AuditLog.Action.UPDATE,
                                'Foto de perfil atualizada',
                                'User',
                                request.user.pk,
                            )

                            if old_path and old_path != new_path:
                                transaction.on_commit(
                                    lambda path=old_path: delete_avatar(path)
                                )

                    except ValidationError as exc:
                        avatar_form.add_error(
                            'avatar',
                            _validation_message(exc),
                        )
                    except ImproperlyConfigured:
                        avatar_form.add_error(
                            None,
                            'O armazenamento de avatares não está '
                            'configurado.',
                        )
                    except Exception:
                        if new_path:
                            delete_avatar(new_path)

                        avatar_form.add_error(
                            None,
                            'Não foi possível enviar a foto. '
                            'Tente novamente.',
                        )
                    else:
                        messages.success(
                            request,
                            'Sua foto de perfil foi atualizada.',
                        )
                        return redirect('accounts:profile')

        else:
            profile_form = ProfileForm(
                request.POST,
                instance=request.user,
                prefix='profile',
            )

            if profile_form.is_valid():
                profile_form.save()
                log_action(
                    request,
                    AuditLog.Action.UPDATE,
                    'Dados pessoais atualizados',
                    'User',
                    request.user.pk,
                )
                messages.success(
                    request,
                    'Seus dados foram atualizados.',
                )
                return redirect('accounts:profile')

    return render(
        request,
        'accounts/profile.html',
        {
            'form': profile_form,
            'avatar_form': avatar_form,
            'can_update_avatar': can_update_avatar,
        },
    )
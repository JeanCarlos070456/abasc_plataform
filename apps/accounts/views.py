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

from .forms import AvatarForm, LoginForm, ProfileForm
from .models import User
from .services import (
    SupabaseAuthError,
    SupabaseAuthService,
    sync_supabase_user,
)



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
@require_http_methods(['GET', 'POST'])
def profile(request):
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
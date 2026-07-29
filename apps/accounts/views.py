from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from django.utils.http import url_has_allowed_host_and_scheme

from apps.core.models import AuditLog
from apps.core.services import log_action
from .forms import LoginForm, ProfileForm
from .models import User
from .services import (
    SupabaseAuthError,
    SupabaseAuthService,
    sync_supabase_user,
)

def _local_sign_in(email, password):
    if not settings.ENABLE_LOCAL_AUTH:
        return None
    try:
        user = User.objects.get(email__iexact=email, is_active=True)
    except User.DoesNotExist:
        return None
    return user if user.check_password(password) else None

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
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(
            request,
            AuditLog.Action.UPDATE,
            'Dados pessoais atualizados',
            'User',
            request.user.pk,
        )
        messages.success(request, 'Seus dados foram atualizados.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html', {'form': form})

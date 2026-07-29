import logging
from dataclasses import dataclass
from uuid import UUID

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

class SupabaseAuthError(Exception):
    pass

@dataclass
class SupabaseSession:
    access_token: str
    refresh_token: str
    user_id: str
    email: str
    user_metadata: dict
    app_metadata: dict

class SupabaseAuthService:
    timeout = 15.0

    @classmethod
    def configured(cls):
        return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY)

    @classmethod
    def sign_in(cls, email: str, password: str) -> SupabaseSession:
        if not cls.configured():
            raise SupabaseAuthError('Supabase Auth não está configurado.')

        endpoint = (
            f'{settings.SUPABASE_URL}/auth/v1/token?grant_type=password'
        )
        headers = {
            'apikey': settings.SUPABASE_ANON_KEY,
            'Content-Type': 'application/json',
        }
        try:
            response = httpx.post(
                endpoint,
                headers=headers,
                json={'email': email, 'password': password},
                timeout=cls.timeout,
            )
        except httpx.HTTPError as exc:
            logger.exception('Falha de comunicação com Supabase Auth')
            raise SupabaseAuthError(
                'Não foi possível acessar o serviço de autenticação.'
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            logger.error(
                'Supabase Auth retornou uma resposta não JSON: %s',
                response.status_code,
            )
            raise SupabaseAuthError(
                'O serviço de autenticação retornou uma resposta inválida.'
            ) from exc

        if not isinstance(data, dict):
            raise SupabaseAuthError(
                'O serviço de autenticação retornou uma resposta inválida.'
            )

        if response.status_code >= 400:
            detail = (
                data.get('msg')
                or data.get('error_description')
                or data.get('message')
            )
            raise SupabaseAuthError(detail or 'E-mail ou senha inválidos.')

        user_data = data.get('user') or {}
        access_token = data.get('access_token', '')
        user_id = user_data.get('id', '')
        if not access_token or not user_id:
            raise SupabaseAuthError(
                'O Supabase não retornou uma sessão válida.'
            )
        return SupabaseSession(
            access_token=access_token,
            refresh_token=data.get('refresh_token', ''),
            user_id=user_id,
            email=user_data.get('email') or email,
            user_metadata=user_data.get('user_metadata') or {},
            app_metadata=user_data.get('app_metadata') or {},
        )

    @classmethod
    def sign_out(cls, access_token: str):
        if not cls.configured() or not access_token:
            return
        try:
            httpx.post(
                f'{settings.SUPABASE_URL}/auth/v1/logout',
                headers={
                    'apikey': settings.SUPABASE_ANON_KEY,
                    'Authorization': f'Bearer {access_token}',
                },
                timeout=cls.timeout,
            )
        except httpx.HTTPError:
            logger.warning(
                'Não foi possível encerrar a sessão remota do Supabase.',
                exc_info=True,
            )

def _safe_uuid(value):
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None

def _normalized_role(value):
    allowed = {choice for choice, _ in User.Role.choices}
    return value if value in allowed else User.Role.ASSOCIATE

def sync_supabase_user(session: SupabaseSession):
    metadata = session.user_metadata or {}
    app_metadata = session.app_metadata or {}
    email = session.email.strip().lower()
    supabase_id = _safe_uuid(session.user_id)
    full_name = metadata.get('name', '').strip()
    name_parts = full_name.split()

    defaults = {
        'username': email,
        'first_name': metadata.get('first_name') or (
            name_parts[0] if name_parts else ''
        ),
        'last_name': metadata.get('last_name') or (
            ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        ),
        'supabase_user_id': supabase_id,
    }
    user, created = User.objects.get_or_create(
        email__iexact=email,
        defaults={**defaults, 'email': email},
    )
    changed_fields = []
    if not created:
        if supabase_id and user.supabase_user_id != supabase_id:
            user.supabase_user_id = supabase_id
            changed_fields.append('supabase_user_id')
        if not user.username:
            user.username = email
            changed_fields.append('username')

    # Apenas app_metadata pode conceder privilégios. user_metadata é
    # editável pelo próprio usuário no Supabase e não deve controlar RBAC.
    metadata_role = app_metadata.get('role')
    if created and metadata_role:
        user.role = _normalized_role(metadata_role)
        changed_fields.append('role')

    user.set_unusable_password()
    changed_fields.append('password')
    if changed_fields:
        user.save(update_fields=list(dict.fromkeys(changed_fields)))
    return user

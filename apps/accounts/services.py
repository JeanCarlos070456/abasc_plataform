import logging
from dataclasses import dataclass
from uuid import UUID

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

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
    """
    Vincula a identidade autenticada no Supabase ao User local.

    Regras importantes para a migração:
    - preserva os dados históricos já importados;
    - vincula pelo supabase_user_id quando ele já existir;
    - caso contrário, vincula pelo e-mail do cadastro local;
    - nunca permite que o mesmo Supabase Auth seja ligado silenciosamente
      a outro User;
    - não altera role, situação associativa, categoria ou onboarding de um
      usuário existente;
    - apenas app_metadata pode definir role na criação de um User novo.
    """
    metadata = session.user_metadata or {}
    app_metadata = session.app_metadata or {}
    email = (session.email or "").strip().lower()
    supabase_id = _safe_uuid(session.user_id)

    if not email:
        raise SupabaseAuthError(
            "O Supabase não retornou o e-mail da conta autenticada."
        )

    if not supabase_id:
        raise SupabaseAuthError(
            "O Supabase não retornou um identificador de usuário válido."
        )

    full_name = (metadata.get("name") or "").strip()
    name_parts = full_name.split()

    defaults = {
        "username": email,
        "first_name": metadata.get("first_name") or (
            name_parts[0] if name_parts else ""
        ),
        "last_name": metadata.get("last_name") or (
            " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        ),
        "supabase_user_id": supabase_id,
    }

    with transaction.atomic():
        by_supabase = (
            User.objects.select_for_update()
            .filter(supabase_user_id=supabase_id)
            .first()
        )
        by_email = (
            User.objects.select_for_update()
            .filter(email__iexact=email)
            .first()
        )

        # Um ID Auth já ligado a uma pessoa não pode ser reassociado apenas
        # porque outro registro possui o mesmo e-mail.
        if (
            by_supabase is not None
            and by_email is not None
            and by_supabase.pk != by_email.pk
        ):
            logger.error(
                "Conflito de identidade Supabase/Django: auth=%s, "
                "user_por_auth=%s, user_por_email=%s.",
                supabase_id,
                by_supabase.pk,
                by_email.pk,
            )
            raise SupabaseAuthError(
                "Existe um conflito entre sua identidade de acesso e o "
                "cadastro da ABASC. Entre em contato com a administração."
            )

        if by_supabase is not None:
            user = by_supabase
            created = False

            # Não trocamos automaticamente o e-mail de um cadastro existente.
            # Isso evita que uma alteração externa no Auth reatribua uma
            # identidade histórica para outro endereço sem revisão.
            if user.email.strip().lower() != email:
                logger.warning(
                    "E-mail divergente para Supabase Auth %s: local=%s, auth=%s.",
                    supabase_id,
                    user.email,
                    email,
                )
                raise SupabaseAuthError(
                    "O e-mail da autenticação não corresponde ao cadastro "
                    "da ABASC. Entre em contato com a administração."
                )

        elif by_email is not None:
            user = by_email
            created = False

            if (
                user.supabase_user_id
                and user.supabase_user_id != supabase_id
            ):
                logger.error(
                    "Tentativa de vincular novo Supabase Auth ao User %s. "
                    "Atual=%s, recebido=%s.",
                    user.pk,
                    user.supabase_user_id,
                    supabase_id,
                )
                raise SupabaseAuthError(
                    "Este cadastro já está vinculado a outra identidade de "
                    "acesso. Entre em contato com a administração."
                )

        else:
            user = User(
                email=email,
                **defaults,
            )
            created = True

        changed_fields = []

        if not created:
            if not user.supabase_user_id:
                user.supabase_user_id = supabase_id
                changed_fields.append("supabase_user_id")

            if not user.username:
                user.username = email
                changed_fields.append("username")

            # Dados migrados são preservados. Metadados do Supabase apenas
            # completam nome vazio; nunca sobrescrevem o que veio da base ABASC.
            if not user.first_name and defaults["first_name"]:
                user.first_name = defaults["first_name"]
                changed_fields.append("first_name")

            if not user.last_name and defaults["last_name"]:
                user.last_name = defaults["last_name"]
                changed_fields.append("last_name")

        # user_metadata é editável pelo próprio usuário e não controla RBAC.
        # app_metadata só é considerado quando o User está sendo criado agora.
        metadata_role = app_metadata.get("role")
        if created and metadata_role:
            user.role = _normalized_role(metadata_role)

        # A senha válida vive no Supabase Auth. O hash local Django permanece
        # inutilizável em produção.
        if user.has_usable_password():
            user.set_unusable_password()
            changed_fields.append("password")

        if created:
            user.save()
        elif changed_fields:
            user.save(
                update_fields=list(dict.fromkeys(changed_fields))
            )

    return user

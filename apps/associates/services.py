from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import models, transaction
from django.utils import timezone
from supabase import create_client

from apps.core.storage import (
    create_private_signed_url,
    delete_private_files,
    get_supabase_admin_client,
    upload_private_file,
)
from .models import MembershipApplication, Payment


logger = logging.getLogger(__name__)
User = get_user_model()

ALLOWED_ASSOCIATION_FILES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}


class MembershipProcessingError(Exception):
    pass


@dataclass
class UploadedMembershipFile:
    path: str
    original_name: str
    content_type: str
    size: int


def get_associations_bucket() -> str:
    return getattr(
        settings,
        "SUPABASE_STORAGE_BUCKET_ASSOCIATIONS",
        "abasc-associations",
    )


def upload_application_file(uploaded_file, *, kind: str, max_size: int):
    application_folder = timezone.now().strftime("%Y/%m")
    path = upload_private_file(
        uploaded_file,
        bucket=get_associations_bucket(),
        folder=f"solicitacoes/{application_folder}/{kind}",
        allowed_content_types=ALLOWED_ASSOCIATION_FILES,
        max_size=max_size,
    )
    return UploadedMembershipFile(
        path=path,
        original_name=Path(uploaded_file.name).name[:255],
        content_type=(uploaded_file.content_type or "")[:100],
        size=uploaded_file.size,
    )


def signed_application_file_url(path: str, *, expires_in: int = 300) -> str:
    return create_private_signed_url(
        path,
        bucket=get_associations_bucket(),
        expires_in=expires_in,
    )


def delete_application_files(*paths: str) -> bool:
    return delete_private_files(
        list(paths),
        bucket=get_associations_bucket(),
    )


def _extract_auth_user(response):
    direct_user = getattr(response, "user", None)
    if direct_user:
        return direct_user

    data = getattr(response, "data", None)
    if data:
        user = getattr(data, "user", None)
        if user:
            return user
        if isinstance(data, dict) and data.get("user"):
            return data["user"]

    if isinstance(response, dict):
        return response.get("user") or (response.get("data") or {}).get("user")
    return None


def _user_value(user, field):
    if isinstance(user, dict):
        return user.get(field)
    return getattr(user, field, None)


def _find_supabase_user(email: str):
    response = get_supabase_admin_client().auth.admin.list_users(
        page=1,
        per_page=1000,
    )
    users = getattr(response, "users", None)
    if users is None:
        data = getattr(response, "data", None)
        users = getattr(data, "users", None) if data else None
    if users is None and isinstance(response, dict):
        users = response.get("users") or (response.get("data") or {}).get("users")
    if users is None and isinstance(response, list):
        users = response

    for auth_user in users or []:
        auth_email = (_user_value(auth_user, "email") or "").lower()
        if auth_email == email.lower():
            return auth_user
    return None


def password_setup_url() -> str:
    site_url = getattr(settings, "ABASC_SITE_URL", "").strip().rstrip("/")
    if not site_url:
        raise MembershipProcessingError(
            "ABASC_SITE_URL não está configurada."
        )
    return f"{site_url}/conta/criar-senha/"


def ensure_supabase_invite(email: str) -> tuple[str, bool]:
    auth_user = _find_supabase_user(email)
    invited = False

    if auth_user is None:
        response = (
            get_supabase_admin_client()
            .auth.admin.invite_user_by_email(
                email,
                {"redirect_to": password_setup_url()},
            )
        )
        auth_user = _extract_auth_user(response)
        invited = True

    user_id = _user_value(auth_user, "id")
    if not user_id:
        raise MembershipProcessingError(
            "O Supabase não retornou o identificador do usuário convidado."
        )

    return str(user_id), invited


def resend_member_access(user) -> str:
    """
    Envia um novo acesso para um associado já aprovado.

    - Se a identidade Auth não existir mais, envia um novo convite.
    - Se já existir, envia um link de recuperação para criar/trocar a senha.
    """
    email = (user.email or "").strip().lower()
    if not email:
        raise MembershipProcessingError(
            "O associado não possui e-mail cadastrado."
        )

    redirect_to = password_setup_url()
    auth_user = _find_supabase_user(email)

    try:
        if auth_user is None:
            response = (
                get_supabase_admin_client()
                .auth.admin.invite_user_by_email(
                    email,
                    {"redirect_to": redirect_to},
                )
            )
            auth_user = _extract_auth_user(response)
            user_id = _user_value(auth_user, "id")

            if not user_id:
                raise MembershipProcessingError(
                    "O Supabase não retornou o usuário convidado."
                )

            user.supabase_user_id = str(user_id)
            user.save(update_fields=[
                "supabase_user_id",
                "profile_updated_at",
            ])
            return "invite"

        client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY,
        )
        client.auth.reset_password_for_email(
            email,
            {"redirect_to": redirect_to},
        )
        return "recovery"

    except MembershipProcessingError:
        raise
    except Exception as exc:
        logger.exception(
            "Falha ao reenviar acesso para %s.",
            email,
        )
        raise MembershipProcessingError(
            "Não foi possível enviar um novo link de acesso. "
            "Aguarde alguns instantes e tente novamente."
        ) from exc



def send_approval_email(user, *, invited: bool):
    login_url = getattr(settings, "ABASC_SITE_URL", "").rstrip("/")
    if login_url:
        login_url = f"{login_url}/conta/login/"

    access_text = (
        "O Supabase também enviará um convite para você definir seu acesso."
        if invited
        else "Sua credencial existente continua válida para acessar a plataforma."
    )
    body = (
        f"Olá, {user.first_name or user.email}!\n\n"
        "Sua associação à ABASC foi aprovada.\n"
        f"Matrícula: {user.membership_number or 'em processamento'}\n"
        f"Função: {user.get_role_display()}\n\n"
        f"{access_text}\n"
    )
    if login_url:
        body += f"Acesso: {login_url}\n"
    body += "\nSeja bem-vinda(o) à ABASC!"

    try:
        send_mail(
            subject="Sua associação à ABASC foi aprovada",
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Falha ao enviar e-mail de aprovação para %s.", user.email)


def _split_name(full_name: str):
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def _association_joined_value(user):
    field = user._meta.get_field("joined_association_at")
    if isinstance(field, models.DateTimeField):
        return timezone.now()
    return timezone.localdate()


def _generate_membership_number(user):
    if user.membership_number:
        return user.membership_number

    year = timezone.localdate().year
    base = f"ABASC-{year}-{user.pk:05d}"
    candidate = base
    suffix = 2
    while User.objects.exclude(pk=user.pk).filter(
        membership_number=candidate
    ).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def approve_application(
    application: MembershipApplication,
    *,
    reviewer,
    target_role: str,
    decision_notes: str = "",
):
    if not application.is_pending:
        raise MembershipProcessingError("Esta solicitação já foi analisada.")

    allowed_roles = {"associate", "executive"}
    if getattr(reviewer, "is_president", False):
        allowed_roles.add("president")
    if target_role not in allowed_roles:
        raise MembershipProcessingError(
            "Você não possui permissão para atribuir essa função."
        )

    try:
        supabase_user_id, invited = ensure_supabase_invite(application.email)
    except Exception as exc:
        logger.exception("Falha ao convidar associado pelo Supabase Auth.")
        raise MembershipProcessingError(
            "Não foi possível criar ou localizar o acesso no Supabase Auth."
        ) from exc

    first_name, last_name = _split_name(application.full_name)

    with transaction.atomic():
        matched_users = list(
            User.objects.select_for_update().filter(
                models.Q(email__iexact=application.email)
                | models.Q(cpf=application.cpf)
            )[:2]
        )
        if len(matched_users) > 1:
            raise MembershipProcessingError(
                "E-mail e CPF estão vinculados a cadastros diferentes. Revise os dados."
            )

        user = matched_users[0] if matched_users else None
        is_new_user = user is None
        if is_new_user:
            user = User(
                username=application.email.lower(),
                email=application.email.lower(),
            )
            user.set_unusable_password()

        user.email = application.email.lower()
        desired_username = application.email.lower()
        if is_new_user or not User.objects.exclude(pk=user.pk).filter(
            username=desired_username
        ).exists():
            user.username = desired_username
        user.first_name = first_name
        user.last_name = last_name
        user.supabase_user_id = supabase_user_id
        user.role = target_role
        user.association_status = "active"
        user.phone = application.whatsapp
        user.cpf = application.cpf
        user.city = application.city
        user.state = application.state
        user.is_active = True
        user.is_staff = target_role in {"executive", "president"}
        user.is_superuser = target_role == "president"

        if not user.joined_association_at:
            user.joined_association_at = _association_joined_value(user)

        user.save()

        if not user.membership_number:
            user.membership_number = _generate_membership_number(user)
            user.save(update_fields=["membership_number"])

        reference_month = timezone.localdate().replace(day=1)
        Payment.objects.update_or_create(
            associate=user,
            reference_month=reference_month,
            defaults={
                "due_date": timezone.localdate(),
                "paid_at": timezone.localdate(),
                "amount": application.amount,
                "status": Payment.Status.PAID,
                "notes": (
                    "Pagamento informado na solicitação de associação "
                    f"#{application.pk}."
                ),
            },
        )

        application.status = MembershipApplication.Status.APPROVED
        application.reviewed_at = timezone.now()
        application.reviewed_by = reviewer
        application.approved_user = user
        application.decision_notes = decision_notes
        application.save(update_fields=[
            "status",
            "reviewed_at",
            "reviewed_by",
            "approved_user",
            "decision_notes",
        ])

    transaction.on_commit(lambda: send_approval_email(user, invited=invited))
    return user


def change_member_role(*, actor, member, new_role: str):
    allowed_roles = {"associate", "executive"}
    if getattr(actor, "is_president", False):
        allowed_roles.add("president")

    if new_role not in allowed_roles:
        raise MembershipProcessingError(
            "Você não possui permissão para atribuir essa função."
        )

    if member.role == "president" and not getattr(actor, "is_president", False):
        raise MembershipProcessingError(
            "Somente a presidência pode alterar outro presidente."
        )

    if member.role == "president" and new_role != "president":
        active_presidents = User.objects.filter(
            role="president",
            association_status="active",
            is_active=True,
        ).count()
        if active_presidents <= 1:
            raise MembershipProcessingError(
                "Não é possível remover a função do último presidente ativo."
            )

    member.role = new_role
    member.is_staff = new_role in {"executive", "president"}
    member.is_superuser = new_role == "president"
    member.save(update_fields=["role", "is_staff", "is_superuser"])
    return member
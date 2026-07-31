import logging

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.functional import cached_property


logger = logging.getLogger(__name__)


class User(AbstractUser):
    class Role(models.TextChoices):
        ASSOCIATE = 'associate', 'Associado'
        EXECUTIVE = 'executive', 'Executivo'
        PRESIDENT = 'president', 'Presidente'

    class AssociationStatus(models.TextChoices):
        ACTIVE = 'active', 'Ativo'
        PENDING = 'pending', 'Pendente'
        OVERDUE = 'overdue', 'Inadimplente'
        INACTIVE = 'inactive', 'Inativo'

    email = models.EmailField('e-mail', unique=True)
    supabase_user_id = models.UUIDField(
        'ID Supabase',
        null=True,
        blank=True,
        unique=True,
    )
    role = models.CharField(
        'perfil',
        max_length=20,
        choices=Role.choices,
        default=Role.ASSOCIATE,
    )
    membership_number = models.CharField(
        'número de associado',
        max_length=30,
        blank=True,
        unique=True,
        null=True,
    )
    association_status = models.CharField(
        'situação associativa',
        max_length=20,
        choices=AssociationStatus.choices,
        default=AssociationStatus.PENDING,
    )
    phone = models.CharField('telefone', max_length=30, blank=True)
    cpf = models.CharField('CPF', max_length=14, blank=True)
    profession = models.CharField('profissão', max_length=120, blank=True)
    city = models.CharField('cidade', max_length=100, blank=True)
    state = models.CharField('UF', max_length=2, blank=True)
    joined_association_at = models.DateField(
        'data de associação',
        null=True,
        blank=True,
    )

    # Mantido para compatibilidade com perfis antigos que usavam URL pública.
    avatar_url = models.URLField('avatar legado', blank=True)

    # Caminho interno no bucket privado abasc-avatars.
    avatar_path = models.CharField(
        'caminho do avatar',
        max_length=500,
        blank=True,
    )

    profile_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'
        ordering = ['first_name', 'last_name', 'email']

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if self.state:
            self.state = self.state.strip().upper()
        if not self.username and self.email:
            self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def display_name(self):
        return self.get_full_name() or self.email.split('@')[0]

    @property
    def role_level(self):
        return {
            self.Role.ASSOCIATE: 10,
            self.Role.EXECUTIVE: 20,
            self.Role.PRESIDENT: 30,
        }.get(self.role, 0)

    def has_role(self, minimum_role):
        levels = {
            self.Role.ASSOCIATE: 10,
            self.Role.EXECUTIVE: 20,
            self.Role.PRESIDENT: 30,
        }
        return self.is_superuser or self.role_level >= levels.get(
            minimum_role,
            999,
        )

    @property
    def can_manage_content(self):
        return self.has_role(self.Role.EXECUTIVE)

    @property
    def is_president(self):
        return self.is_superuser or self.role == self.Role.PRESIDENT

    @property
    def can_update_avatar(self):
        return (
            self.is_active
            and self.association_status == self.AssociationStatus.ACTIVE
        )

    @cached_property
    def display_avatar_url(self):
        """
        Retorna uma URL temporária para o avatar privado.

        Perfis antigos que ainda possuam avatar_url continuam funcionando.
        """
        if not self.avatar_path:
            return self.avatar_url

        try:
            from apps.core.storage import create_avatar_signed_url

            return create_avatar_signed_url(
                self.avatar_path,
                expires_in=3600,
            )
        except Exception:
            logger.exception(
                'Não foi possível gerar a URL do avatar do usuário %s.',
                self.pk,
            )
            return self.avatar_url
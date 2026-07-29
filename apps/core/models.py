from django.conf import settings
from django.db import models

class SiteConfiguration(models.Model):
    site_name = models.CharField('nome do site', max_length=120, default='ABASC')
    full_name = models.CharField(
        'nome completo',
        max_length=255,
        default='Associação de Bacharéis em Saúde Coletiva',
    )
    contact_email = models.EmailField(
        'e-mail de contato',
        default='abasc.comunica@gmail.com',
    )
    contact_phone = models.CharField('telefone', max_length=30, blank=True)
    address = models.CharField('endereço', max_length=255, blank=True)
    instagram_url = models.URLField('Instagram', blank=True)
    linkedin_url = models.URLField('LinkedIn', blank=True)
    youtube_url = models.URLField('YouTube', blank=True)
    x_url = models.URLField('X/Twitter', blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'configuração do site'
        verbose_name_plural = 'configurações do site'

    def __str__(self):
        return self.site_name

    @classmethod
    def current(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        CREATE = 'create', 'Criação'
        UPDATE = 'update', 'Atualização'
        DELETE = 'delete', 'Exclusão'
        ROLE_CHANGE = 'role_change', 'Alteração de perfil'

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_entries',
    )
    action = models.CharField('ação', max_length=30, choices=Action.choices)
    description = models.CharField('descrição', max_length=255)
    object_type = models.CharField('tipo de objeto', max_length=80, blank=True)
    object_id = models.CharField('ID do objeto', max_length=80, blank=True)
    ip_address = models.GenericIPAddressField('IP', null=True, blank=True)
    created_at = models.DateTimeField('data', auto_now_add=True)

    class Meta:
        verbose_name = 'registro de auditoria'
        verbose_name_plural = 'registros de auditoria'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_action_display()} — {self.description}'

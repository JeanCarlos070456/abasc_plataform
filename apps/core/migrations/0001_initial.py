from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteConfiguration',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('site_name', models.CharField(default='ABASC', max_length=120, verbose_name='nome do site')),
                (
                    'full_name',
                    models.CharField(
                        default='Associação de Bacharéis em Saúde Coletiva',
                        max_length=255,
                        verbose_name='nome completo',
                    ),
                ),
                (
                    'contact_email',
                    models.EmailField(
                        default='abasc.comunica@gmail.com',
                        max_length=254,
                        verbose_name='e-mail de contato',
                    ),
                ),
                ('contact_phone', models.CharField(blank=True, max_length=30, verbose_name='telefone')),
                ('address', models.CharField(blank=True, max_length=255, verbose_name='endereço')),
                ('instagram_url', models.URLField(blank=True, verbose_name='Instagram')),
                ('linkedin_url', models.URLField(blank=True, verbose_name='LinkedIn')),
                ('youtube_url', models.URLField(blank=True, verbose_name='YouTube')),
                ('x_url', models.URLField(blank=True, verbose_name='X/Twitter')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'configuração do site',
                'verbose_name_plural': 'configurações do site',
            },
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'action',
                    models.CharField(
                        choices=[
                            ('login', 'Login'),
                            ('logout', 'Logout'),
                            ('create', 'Criação'),
                            ('update', 'Atualização'),
                            ('delete', 'Exclusão'),
                            ('role_change', 'Alteração de perfil'),
                        ],
                        max_length=30,
                        verbose_name='ação',
                    ),
                ),
                ('description', models.CharField(max_length=255, verbose_name='descrição')),
                ('object_type', models.CharField(blank=True, max_length=80, verbose_name='tipo de objeto')),
                ('object_id', models.CharField(blank=True, max_length=80, verbose_name='ID do objeto')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='data')),
                (
                    'actor',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='audit_entries',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'registro de auditoria',
                'verbose_name_plural': 'registros de auditoria',
                'ordering': ['-created_at'],
            },
        ),
    ]

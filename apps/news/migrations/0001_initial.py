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
            name='Category',
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
                ('name', models.CharField(max_length=80, unique=True, verbose_name='nome')),
                ('slug', models.SlugField(blank=True, max_length=90, unique=True)),
                ('description', models.CharField(blank=True, max_length=180, verbose_name='descrição')),
                ('active', models.BooleanField(default=True, verbose_name='ativa')),
            ],
            options={
                'verbose_name': 'categoria',
                'verbose_name_plural': 'categorias',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Post',
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
                ('title', models.CharField(max_length=180, verbose_name='título')),
                ('slug', models.SlugField(blank=True, max_length=200, unique=True)),
                ('summary', models.CharField(max_length=300, verbose_name='resumo')),
                ('body', models.TextField(verbose_name='conteúdo')),
                ('external_url', models.URLField(blank=True, verbose_name='link externo')),
                ('image_url', models.URLField(blank=True, max_length=500, verbose_name='URL da imagem')),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('draft', 'Rascunho'),
                            ('published', 'Publicado'),
                            ('archived', 'Arquivado'),
                        ],
                        default='draft',
                        max_length=20,
                        verbose_name='status',
                    ),
                ),
                (
                    'visibility',
                    models.CharField(
                        choices=[
                            ('public', 'Público'),
                            ('associates', 'Somente associados'),
                            ('executives', 'Executivo e presidência'),
                        ],
                        default='public',
                        max_length=20,
                        verbose_name='visibilidade',
                    ),
                ),
                ('featured', models.BooleanField(default=False, verbose_name='destaque')),
                (
                    'is_opportunity',
                    models.BooleanField(default=False, verbose_name='oportunidade/processo seletivo'),
                ),
                ('published_at', models.DateTimeField(blank=True, null=True, verbose_name='publicado em')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                (
                    'author',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='authored_posts',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='autor',
                    ),
                ),
                (
                    'category',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='posts',
                        to='news.category',
                        verbose_name='categoria',
                    ),
                ),
            ],
            options={
                'verbose_name': 'publicação',
                'verbose_name_plural': 'publicações',
                'ordering': ['-published_at', '-created_at'],
                'indexes': [
                    models.Index(
                        fields=['status', 'visibility', '-published_at'],
                        name='news_post_status_vis_pub_idx',
                    ),
                    models.Index(
                        fields=['featured', '-published_at'],
                        name='news_post_featured_pub_idx',
                    ),
                    models.Index(
                        fields=['is_opportunity', '-published_at'],
                        name='news_post_opport_pub_idx',
                    ),
                ],
            },
        ),
    ]

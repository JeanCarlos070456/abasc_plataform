from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField('nome', max_length=80, unique=True)
    slug = models.SlugField(unique=True, max_length=90, blank=True)
    description = models.CharField('descrição', max_length=180, blank=True)
    active = models.BooleanField('ativa', default=True)

    class Meta:
        verbose_name = 'categoria'
        verbose_name_plural = 'categorias'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:80] or 'categoria'
            candidate = base
            counter = 2
            while Category.objects.exclude(pk=self.pk).filter(
                slug=candidate
            ).exists():
                suffix = f'-{counter}'
                candidate = f'{base[:90 - len(suffix)]}{suffix}'
                counter += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class PostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(
            status=Post.Status.PUBLISHED,
            published_at__lte=timezone.now(),
        )

    def visible_to(self, user):
        queryset = self.published().select_related('category', 'author')
        if user and user.is_authenticated:
            if user.is_president or user.can_manage_content:
                return queryset
            return queryset.filter(
                visibility__in=[
                    Post.Visibility.PUBLIC,
                    Post.Visibility.ASSOCIATES,
                ]
            )
        return queryset.filter(visibility=Post.Visibility.PUBLIC)

class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Rascunho'
        PUBLISHED = 'published', 'Publicado'
        ARCHIVED = 'archived', 'Arquivado'

    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Público'
        ASSOCIATES = 'associates', 'Somente associados'
        EXECUTIVES = 'executives', 'Executivo e presidência'

    title = models.CharField('título', max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    summary = models.CharField('resumo', max_length=300)
    body = models.TextField('conteúdo')
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='posts',
        verbose_name='categoria',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='authored_posts',
        verbose_name='autor',
    )
    external_url = models.URLField('link externo', blank=True)
    image_url = models.URLField(
        'URL da imagem',
        max_length=500,
        blank=True,
    )
    status = models.CharField(
        'status',
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    visibility = models.CharField(
        'visibilidade',
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    featured = models.BooleanField('destaque', default=False)
    is_opportunity = models.BooleanField(
        'oportunidade/processo seletivo',
        default=False,
    )
    published_at = models.DateTimeField(
        'publicado em',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        verbose_name = 'publicação'
        verbose_name_plural = 'publicações'
        ordering = ['-published_at', '-created_at']
        indexes = [
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
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:170] or 'publicacao'
            candidate = base
            counter = 2
            while Post.objects.exclude(pk=self.pk).filter(
                slug=candidate
            ).exists():
                candidate = f'{base}-{counter}'
                counter += 1
            self.slug = candidate
        if (
            self.status == self.Status.PUBLISHED
            and not self.published_at
        ):
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse(
            'news:detail',
            kwargs={'slug': self.slug},
        )

    @property
    def cover_url(self):
        return self.image_url or '/static/img/news-placeholder.svg'

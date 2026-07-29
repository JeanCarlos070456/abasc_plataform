from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from .models import Category, Post

class NewsTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Institucional')
        self.author = User.objects.create_user(
            username='exec@example.com',
            email='exec@example.com',
            password='StrongPass123',
            role=User.Role.EXECUTIVE,
        )
        self.post = Post.objects.create(
            title='Notícia pública',
            summary='Resumo',
            body='Conteúdo',
            category=self.category,
            author=self.author,
            status=Post.Status.PUBLISHED,
            visibility=Post.Visibility.PUBLIC,
            published_at=timezone.now(),
        )

    def test_public_post_is_visible(self):
        response = self.client.get(
            reverse(
                'news:detail',
                kwargs={'slug': self.post.slug},
            )
        )
        self.assertEqual(response.status_code, 200)


    def test_public_cannot_open_associate_only_post(self):
        restricted = Post.objects.create(
            title='Comunicado restrito',
            summary='Resumo restrito',
            body='Conteúdo restrito',
            category=self.category,
            author=self.author,
            status=Post.Status.PUBLISHED,
            visibility=Post.Visibility.ASSOCIATES,
            published_at=timezone.now(),
        )
        response = self.client.get(
            reverse('news:detail', kwargs={'slug': restricted.slug})
        )
        self.assertEqual(response.status_code, 404)

    def test_associate_cannot_manage_posts(self):
        associate = User.objects.create_user(
            username='assoc@example.com',
            email='assoc@example.com',
            password='StrongPass123',
        )
        self.client.force_login(associate)
        response = self.client.get(reverse('news:manage'))
        self.assertEqual(response.status_code, 403)

    def test_executive_can_open_create_form(self):
        self.client.force_login(self.author)
        response = self.client.get(reverse('news:create'))
        self.assertEqual(response.status_code, 200)

from django.urls import path
from . import views

app_name = 'news'
urlpatterns = [
    path('', views.post_list, name='list'),
    path(
        'publicacao/<slug:slug>/',
        views.post_detail,
        name='detail',
    ),
    path('gestao/', views.manage_posts, name='manage'),
    path('gestao/nova/', views.create_post, name='create'),
    path(
        'gestao/<int:pk>/editar/',
        views.update_post,
        name='update',
    ),
    path(
        'gestao/<int:pk>/excluir/',
        views.delete_post,
        name='delete',
    ),
    path(
        'gestao/<int:pk>/alternar-publicacao/',
        views.toggle_publish,
        name='toggle_publish',
    ),
    path(
        'gestao/categorias/',
        views.categories,
        name='categories',
    ),
]

from django.urls import path

from . import views


app_name = 'accounts'

urlpatterns = [
    path('entrar/', views.login_view, name='login'),
    path('sair/', views.logout_view, name='logout'),
    path('direcionar/', views.post_login, name='post_login'),
    path('meus-dados/', views.profile, name='profile'),
    path(
        'criar-senha/',
        views.create_password,
        name='create_password',
    ),
]
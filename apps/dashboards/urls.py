from django.urls import path
from . import views

app_name = 'dashboards'
urlpatterns = [
    path(
        'executivo/',
        views.executive_dashboard,
        name='executive',
    ),
    path(
        'presidencia/',
        views.president_dashboard,
        name='president',
    ),
    path(
        'presidencia/usuarios/',
        views.users,
        name='users',
    ),
    path(
        'presidencia/usuarios/<int:pk>/editar/',
        views.update_user,
        name='update_user',
    ),
]

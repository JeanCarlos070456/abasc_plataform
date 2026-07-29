from django.urls import path
from . import views

app_name = 'associates'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path(
        'pagamentos/',
        views.manage_payments,
        name='manage_payments',
    ),
    path(
        'pagamentos/novo/',
        views.create_payment,
        name='create_payment',
    ),
    path(
        'pagamentos/<int:pk>/editar/',
        views.update_payment,
        name='update_payment',
    ),
]

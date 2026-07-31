from django.urls import path

from . import views


app_name = "associates"

urlpatterns = [
    path("associar/", views.join, name="join"),
    path(
        "associar/enviada/<uuid:public_id>/",
        views.application_submitted,
        name="application_submitted",
    ),
    path("", views.dashboard, name="dashboard"),
    path(
        "gestao/solicitacoes/",
        views.manage_applications,
        name="manage_applications",
    ),
    path(
        "gestao/solicitacoes/<int:pk>/",
        views.application_detail,
        name="application_detail",
    ),
    path(
        "gestao/solicitacoes/<int:pk>/reenviar-acesso/",
        views.resend_application_access,
        name="resend_application_access",
    ),
    path(
        "gestao/solicitacoes/<int:pk>/rejeitar/",
        views.reject_application,
        name="reject_application",
    ),
    path(
        "gestao/membros/",
        views.manage_members,
        name="manage_members",
    ),
    path(
        "gestao/membros/<int:pk>/funcao/",
        views.update_member_role,
        name="update_member_role",
    ),
    path(
        "pagamentos/",
        views.manage_payments,
        name="manage_payments",
    ),
    path(
        "pagamentos/novo/",
        views.create_payment,
        name="create_payment",
    ),
    path(
        "pagamentos/<int:pk>/editar/",
        views.update_payment,
        name="update_payment",
    ),
]
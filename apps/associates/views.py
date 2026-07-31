from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.decorators import associate_required, executive_required
from apps.core.models import AuditLog
from apps.core.services import log_action
from apps.news.models import Post
from .forms import (
    MemberRoleForm,
    MembershipApplicationForm,
    MembershipReviewForm,
    PaymentForm,
)
from .models import MembershipApplication, Payment
from .services import (
    MembershipProcessingError,
    approve_application,
    change_member_role,
    resend_member_access,
    delete_application_files,
    signed_application_file_url,
    upload_application_file,
)


User = get_user_model()


@require_http_methods(["GET", "POST"])
def join(request):
    form = MembershipApplicationForm(
        request.POST or None,
        request.FILES or None,
    )

    if request.method == "POST" and form.is_valid():
        document = form.cleaned_data["supporting_document"]
        receipt = form.cleaned_data["payment_receipt"]
        uploaded_paths = []

        try:
            document_data = upload_application_file(
                document,
                kind="documentos",
                max_size=100 * 1024 * 1024,
            )
            uploaded_paths.append(document_data.path)

            receipt_data = upload_application_file(
                receipt,
                kind="comprovantes",
                max_size=10 * 1024 * 1024,
            )
            uploaded_paths.append(receipt_data.path)
        except Exception:
            delete_application_files(*uploaded_paths)
            form.add_error(
                None,
                "Não foi possível enviar os arquivos. Tente novamente.",
            )
        else:
            try:
                with transaction.atomic():
                    application = form.save(commit=False)
                    application.supporting_document_path = document_data.path
                    application.supporting_document_name = document_data.original_name
                    application.supporting_document_content_type = document_data.content_type
                    application.supporting_document_size = document_data.size
                    application.payment_receipt_path = receipt_data.path
                    application.payment_receipt_name = receipt_data.original_name
                    application.payment_receipt_content_type = receipt_data.content_type
                    application.payment_receipt_size = receipt_data.size
                    application.full_clean()
                    application.save()

            except Exception:
                delete_application_files(*uploaded_paths)
                form.add_error(
                    None,
                    "Não foi possível registrar a solicitação. Tente novamente.",
                )
            else:
                messages.success(
                    request,
                    "Solicitação enviada com sucesso. A diretoria analisará os dados.",
                )
                return redirect(
                    "associates:application_submitted",
                    public_id=application.public_id,
                )

    context = {
        "form": form,
        "pix_key": getattr(
            settings,
            "ABASC_PIX_KEY",
            "35.848.139/0001-74",
        ),
        "pix_name": getattr(
            settings,
            "ABASC_PIX_NAME",
            "Associação de Bacharéis em Saúde Coletiva",
        ),
        "contact_email": getattr(
            settings,
            "ABASC_CONTACT_EMAIL",
            "diretoria@abascsaudecoletiva.com",
        ),
        "contact_phone": getattr(
            settings,
            "ABASC_CONTACT_PHONE",
            "(61) 98158-3258",
        ),
    }
    return render(request, "associates/join.html", context)


def application_submitted(request, public_id):
    application = get_object_or_404(
        MembershipApplication,
        public_id=public_id,
    )
    return render(
        request,
        "associates/application_submitted.html",
        {"application": application},
    )


@associate_required
def dashboard(request):
    payments = request.user.payments.all()
    last_payment = payments.filter(
        status=Payment.Status.PAID
    ).order_by("-paid_at").first()
    next_payment = payments.filter(
        status__in=[Payment.Status.PENDING, Payment.Status.OVERDUE]
    ).order_by("due_date").first()
    member_posts = Post.objects.visible_to(request.user).exclude(
        visibility=Post.Visibility.PUBLIC
    )[:4]
    return render(request, "associates/dashboard.html", {
        "payments": payments[:12],
        "last_payment": last_payment,
        "next_payment": next_payment,
        "member_posts": member_posts,
        "today": timezone.localdate(),
    })


@executive_required
def manage_applications(request):
    status = request.GET.get("status", MembershipApplication.Status.PENDING)
    applications = MembershipApplication.objects.select_related(
        "reviewed_by",
        "approved_user",
    )
    if status in dict(MembershipApplication.Status.choices):
        applications = applications.filter(status=status)
    else:
        status = ""

    return render(request, "associates/application_list.html", {
        "applications": applications,
        "selected_status": status,
        "pending_count": MembershipApplication.objects.filter(
            status=MembershipApplication.Status.PENDING
        ).count(),
    })


@executive_required
@require_http_methods(["GET", "POST"])
def application_detail(request, pk):
    application = get_object_or_404(
        MembershipApplication.objects.select_related(
            "reviewed_by",
            "approved_user",
        ),
        pk=pk,
    )
    review_form = MembershipReviewForm(
        request.POST or None,
        actor=request.user,
    )

    try:
        document_url = signed_application_file_url(
            application.supporting_document_path
        )
        receipt_url = signed_application_file_url(
            application.payment_receipt_path
        )
    except Exception:
        document_url = ""
        receipt_url = ""
        messages.warning(
            request,
            "Não foi possível gerar os links temporários dos arquivos.",
        )

    if request.method == "POST" and request.POST.get("action") == "approve":
        if review_form.is_valid():
            try:
                user = approve_application(
                    application,
                    reviewer=request.user,
                    target_role=review_form.cleaned_data["target_role"],
                    decision_notes=review_form.cleaned_data["decision_notes"],
                )
            except MembershipProcessingError as exc:
                review_form.add_error(None, str(exc))
            else:
                log_action(
                    request,
                    AuditLog.Action.UPDATE,
                    f"Solicitação de associação aprovada: #{application.pk}",
                    "MembershipApplication",
                    application.pk,
                )
                messages.success(
                    request,
                    f"Solicitação aprovada. {user.email} foi convidado para acessar o sistema.",
                )
                return redirect("associates:manage_applications")

    return render(request, "associates/application_detail.html", {
        "application": application,
        "review_form": review_form,
        "document_url": document_url,
        "receipt_url": receipt_url,
    })


@executive_required
@require_POST
def resend_application_access(request, pk):
    application = get_object_or_404(
        MembershipApplication.objects.select_related(
            "approved_user",
        ),
        pk=pk,
        status=MembershipApplication.Status.APPROVED,
    )

    if application.approved_user is None:
        messages.error(
            request,
            "Esta solicitação não possui usuário aprovado vinculado.",
        )
        return redirect(
            "associates:application_detail",
            pk=application.pk,
        )

    try:
        delivery_type = resend_member_access(
            application.approved_user
        )
    except MembershipProcessingError as exc:
        messages.error(request, str(exc))
    else:
        log_action(
            request,
            AuditLog.Action.UPDATE,
            (
                "Novo link de acesso enviado para "
                f"{application.approved_user.email}: {delivery_type}"
            ),
            "MembershipApplication",
            application.pk,
        )
        messages.success(
            request,
            "Novo link para criar a senha foi enviado por e-mail.",
        )

    return redirect(
        "associates:application_detail",
        pk=application.pk,
    )


@executive_required
@require_POST
def reject_application(request, pk):
    application = get_object_or_404(
        MembershipApplication,
        pk=pk,
        status=MembershipApplication.Status.PENDING,
    )
    object_id = application.pk
    paths = (
        application.supporting_document_path,
        application.payment_receipt_path,
    )

    with transaction.atomic():
        application.delete()
        log_action(
            request,
            AuditLog.Action.DELETE,
            f"Solicitação de associação rejeitada e removida: #{object_id}",
            "MembershipApplication",
            object_id,
        )
        transaction.on_commit(
            lambda: delete_application_files(*paths)
        )

    messages.success(
        request,
        "Solicitação rejeitada. Os dados e arquivos foram removidos.",
    )
    return redirect("associates:manage_applications")


@executive_required
def manage_members(request):
    members = User.objects.filter(is_active=True).order_by(
        "role",
        "first_name",
        "last_name",
        "email",
    )
    return render(request, "associates/manage_members.html", {
        "members": members,
    })


@executive_required
@require_http_methods(["GET", "POST"])
def update_member_role(request, pk):
    member = get_object_or_404(User, pk=pk, is_active=True)
    form = MemberRoleForm(
        request.POST or None,
        actor=request.user,
        member=member,
    )

    if request.method == "POST" and form.is_valid():
        try:
            change_member_role(
                actor=request.user,
                member=member,
                new_role=form.cleaned_data["role"],
            )
        except MembershipProcessingError as exc:
            form.add_error(None, str(exc))
        else:
            log_action(
                request,
                AuditLog.Action.UPDATE,
                f"Função alterada para {member.email}: {member.role}",
                "User",
                member.pk,
            )
            messages.success(request, "Função do membro atualizada.")
            return redirect("associates:manage_members")

    return render(request, "associates/member_role_form.html", {
        "form": form,
        "member": member,
    })


@executive_required
def manage_payments(request):
    payments = Payment.objects.select_related("associate").all()
    return render(
        request,
        "associates/manage_payments.html",
        {"payments": payments},
    )


@executive_required
@require_http_methods(["GET", "POST"])
def create_payment(request):
    form = PaymentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        payment = form.save()
        log_action(
            request,
            AuditLog.Action.CREATE,
            f"Pagamento criado para {payment.associate.email}",
            "Payment",
            payment.pk,
        )
        messages.success(request, "Pagamento cadastrado.")
        return redirect("associates:manage_payments")
    return render(request, "associates/payment_form.html", {
        "form": form,
        "page_title": "Novo pagamento",
    })


@executive_required
@require_http_methods(["GET", "POST"])
def update_payment(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    form = PaymentForm(
        request.POST or None,
        instance=payment,
    )
    if request.method == "POST" and form.is_valid():
        payment = form.save()
        log_action(
            request,
            AuditLog.Action.UPDATE,
            f"Pagamento atualizado para {payment.associate.email}",
            "Payment",
            payment.pk,
        )
        messages.success(request, "Pagamento atualizado.")
        return redirect("associates:manage_payments")
    return render(request, "associates/payment_form.html", {
        "form": form,
        "page_title": "Editar pagamento",
        "payment": payment,
    })
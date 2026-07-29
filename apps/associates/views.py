from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.decorators import (
    associate_required,
    executive_required,
)
from apps.core.models import AuditLog
from apps.core.services import log_action
from apps.news.models import Post
from .forms import PaymentForm
from .models import Payment

@associate_required
def dashboard(request):
    payments = request.user.payments.all()
    last_payment = payments.filter(
        status=Payment.Status.PAID
    ).order_by('-paid_at').first()
    next_payment = payments.filter(
        status__in=[
            Payment.Status.PENDING,
            Payment.Status.OVERDUE,
        ]
    ).order_by('due_date').first()
    member_posts = Post.objects.visible_to(request.user).exclude(
        visibility=Post.Visibility.PUBLIC
    )[:4]
    return render(request, 'associates/dashboard.html', {
        'payments': payments[:12],
        'last_payment': last_payment,
        'next_payment': next_payment,
        'member_posts': member_posts,
        'today': timezone.localdate(),
    })

@executive_required
def manage_payments(request):
    payments = Payment.objects.select_related('associate').all()
    return render(
        request,
        'associates/manage_payments.html',
        {'payments': payments},
    )

@executive_required
@require_http_methods(['GET', 'POST'])
def create_payment(request):
    form = PaymentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        payment = form.save()
        log_action(
            request,
            AuditLog.Action.CREATE,
            f'Pagamento criado para {payment.associate.email}',
            'Payment',
            payment.pk,
        )
        messages.success(request, 'Pagamento cadastrado.')
        return redirect('associates:manage_payments')
    return render(request, 'associates/payment_form.html', {
        'form': form,
        'page_title': 'Novo pagamento',
    })

@executive_required
@require_http_methods(['GET', 'POST'])
def update_payment(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    form = PaymentForm(
        request.POST or None,
        instance=payment,
    )
    if request.method == 'POST' and form.is_valid():
        payment = form.save()
        log_action(
            request,
            AuditLog.Action.UPDATE,
            f'Pagamento atualizado para {payment.associate.email}',
            'Payment',
            payment.pk,
        )
        messages.success(request, 'Pagamento atualizado.')
        return redirect('associates:manage_payments')
    return render(request, 'associates/payment_form.html', {
        'form': form,
        'page_title': 'Editar pagamento',
        'payment': payment,
    })

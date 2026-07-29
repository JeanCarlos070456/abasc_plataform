from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.decorators import (
    executive_required,
    president_required,
)
from apps.accounts.forms import RoleUpdateForm
from apps.accounts.models import User
from apps.associates.models import Payment
from apps.core.models import AuditLog
from apps.core.services import log_action
from apps.news.models import Post

@executive_required
def executive_dashboard(request):
    stats = {
        'active_associates': User.objects.filter(
            role=User.Role.ASSOCIATE,
            association_status=User.AssociationStatus.ACTIVE,
            is_active=True,
        ).count(),
        'overdue_associates': User.objects.filter(
            association_status=User.AssociationStatus.OVERDUE,
            is_active=True,
        ).count(),
        'published_posts': Post.objects.filter(
            status=Post.Status.PUBLISHED
        ).count(),
        'draft_posts': Post.objects.filter(
            status=Post.Status.DRAFT
        ).count(),
    }
    due_payments = Payment.objects.filter(
        status__in=[
            Payment.Status.PENDING,
            Payment.Status.OVERDUE,
        ]
    ).select_related('associate').order_by('due_date')[:8]
    recent_posts = Post.objects.select_related(
        'category',
        'author',
    )[:8]
    recent_associates = User.objects.filter(
        role=User.Role.ASSOCIATE
    ).order_by('-date_joined')[:8]
    return render(request, 'dashboards/executive.html', {
        'stats': stats,
        'due_payments': due_payments,
        'recent_posts': recent_posts,
        'recent_associates': recent_associates,
        'today': timezone.localdate(),
    })

@president_required
def president_dashboard(request):
    paid_total = Payment.objects.filter(
        status=Payment.Status.PAID
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    pending_total = Payment.objects.filter(
        status__in=[
            Payment.Status.PENDING,
            Payment.Status.OVERDUE,
        ]
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    status_rows = User.objects.values(
        'association_status'
    ).annotate(total=Count('id'))
    users_by_status = {
        row['association_status']: row['total']
        for row in status_rows
    }
    max_status = max(users_by_status.values(), default=1)
    status_chart = [{
        'key': key,
        'label': label,
        'count': users_by_status.get(key, 0),
        'percent': round(
            users_by_status.get(key, 0) / max_status * 100
        ),
    } for key, label in User.AssociationStatus.choices]
    stats = {
        'total_users': User.objects.filter(is_active=True).count(),
        'executives': User.objects.filter(
            role=User.Role.EXECUTIVE,
            is_active=True,
        ).count(),
        'paid_total': paid_total,
        'pending_total': pending_total,
    }
    recent_logs = AuditLog.objects.select_related('actor')[:12]
    return render(request, 'dashboards/president.html', {
        'stats': stats,
        'status_chart': status_chart,
        'recent_logs': recent_logs,
    })

@president_required
def users(request):
    query = request.GET.get('q', '').strip()
    users_qs = User.objects.all()
    if query:
        users_qs = users_qs.filter(
            Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
    return render(request, 'dashboards/users.html', {
        'users_list': users_qs,
        'query': query,
    })

@president_required
@require_http_methods(['GET', 'POST'])
def update_user(request, pk):
    managed_user = get_object_or_404(User, pk=pk)
    old_role = managed_user.role
    form = RoleUpdateForm(
        request.POST or None,
        instance=managed_user,
    )
    if request.method == 'POST' and form.is_valid():
        requested_role = form.cleaned_data['role']
        requested_active = form.cleaned_data['is_active']
        currently_president = (
            managed_user.is_superuser
            or old_role == User.Role.PRESIDENT
        )
        will_be_president = (
            managed_user.is_superuser
            or requested_role == User.Role.PRESIDENT
        )

        if managed_user == request.user and (
            not requested_active or not will_be_president
        ):
            form.add_error(
                None,
                'Você não pode remover ou desativar o próprio acesso '
                'presidencial.',
            )
        elif currently_president and (
            not requested_active or not will_be_president
        ):
            another_president_exists = User.objects.filter(
                Q(role=User.Role.PRESIDENT) | Q(is_superuser=True),
                is_active=True,
            ).exclude(pk=managed_user.pk).exists()
            if not another_president_exists:
                form.add_error(
                    None,
                    'O sistema deve manter pelo menos um presidente '
                    'ativo.',
                )

        if not form.errors:
            updated = form.save()
            action = (
                AuditLog.Action.ROLE_CHANGE
                if old_role != updated.role
                else AuditLog.Action.UPDATE
            )
            log_action(
                request,
                action,
                (
                    f'Usuário atualizado: {updated.email} '
                    f'({updated.get_role_display()})'
                ),
                'User',
                updated.pk,
            )
            messages.success(request, 'Usuário atualizado.')
            return redirect('dashboards:users')
    return render(request, 'dashboards/user_form.html', {
        'form': form,
        'managed_user': managed_user,
    })

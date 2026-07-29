from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        PAID = 'paid', 'Pago'
        OVERDUE = 'overdue', 'Vencido'
        CANCELED = 'canceled', 'Cancelado'

    associate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='associado',
    )
    reference_month = models.DateField(
        'mês de referência',
        help_text='Use o primeiro dia do mês.',
    )
    due_date = models.DateField('vencimento')
    paid_at = models.DateField(
        'data do pagamento',
        null=True,
        blank=True,
    )
    amount = models.DecimalField(
        'valor',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    status = models.CharField(
        'status',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    notes = models.CharField(
        'observações',
        max_length=255,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'pagamento'
        verbose_name_plural = 'pagamentos'
        ordering = ['-reference_month']
        constraints = [
            models.UniqueConstraint(
                fields=['associate', 'reference_month'],
                name='uniq_assoc_reference_month',
            )
        ]
        indexes = [
            models.Index(
                fields=['status', 'due_date'],
                name='assoc_pay_status_due_idx',
            ),
            models.Index(
                fields=['associate', '-reference_month'],
                name='assoc_pay_user_ref_idx',
            ),
        ]

    def clean(self):
        super().clean()
        if self.status == self.Status.PAID and not self.paid_at:
            raise ValidationError({
                'paid_at': (
                    'Informe a data do pagamento para um registro pago.'
                )
            })

    def save(self, *args, **kwargs):
        if self.reference_month:
            self.reference_month = self.reference_month.replace(day=1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.associate} — {self.reference_month:%m/%Y}'

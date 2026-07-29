from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'reference_month',
                    models.DateField(
                        help_text='Use o primeiro dia do mês.',
                        verbose_name='mês de referência',
                    ),
                ),
                ('due_date', models.DateField(verbose_name='vencimento')),
                ('paid_at', models.DateField(blank=True, null=True, verbose_name='data do pagamento')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal('0.01'))], verbose_name='valor')),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('pending', 'Pendente'),
                            ('paid', 'Pago'),
                            ('overdue', 'Vencido'),
                            ('canceled', 'Cancelado'),
                        ],
                        default='pending',
                        max_length=20,
                        verbose_name='status',
                    ),
                ),
                ('notes', models.CharField(blank=True, max_length=255, verbose_name='observações')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'associate',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='payments',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='associado',
                    ),
                ),
            ],
            options={
                'verbose_name': 'pagamento',
                'verbose_name_plural': 'pagamentos',
                'ordering': ['-reference_month'],
                'indexes': [
                    models.Index(
                        fields=['status', 'due_date'],
                        name='assoc_pay_status_due_idx',
                    ),
                    models.Index(
                        fields=['associate', '-reference_month'],
                        name='assoc_pay_user_ref_idx',
                    ),
                ],
                'constraints': [
                    models.UniqueConstraint(
                        fields=('associate', 'reference_month'),
                        name='uniq_assoc_reference_month',
                    ),
                ],
            },
        ),
    ]

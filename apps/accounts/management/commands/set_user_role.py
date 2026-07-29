from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Altera o papel de um usuário existente pelo e-mail.'

    def add_arguments(self, parser):
        parser.add_argument('email')
        parser.add_argument(
            'role',
            choices=[choice for choice, _ in User.Role.choices],
        )
        parser.add_argument(
            '--activate',
            action='store_true',
            help='Ativa a conta junto com a alteração.',
        )

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist as exc:
            raise CommandError(
                'Usuário não encontrado. Faça o primeiro login pelo '
                'Supabase Auth para sincronizar a conta.'
            ) from exc

        new_role = options['role']
        currently_president = user.is_superuser or (
            user.role == User.Role.PRESIDENT
        )
        will_be_president = user.is_superuser or (
            new_role == User.Role.PRESIDENT
        )
        if currently_president and not will_be_president:
            another_president_exists = User.objects.filter(
                Q(role=User.Role.PRESIDENT) | Q(is_superuser=True),
                is_active=True,
            ).exclude(pk=user.pk).exists()
            if not another_president_exists:
                raise CommandError(
                    'Não é permitido remover o último presidente ativo.'
                )

        user.role = new_role
        update_fields = ['role']
        if options['activate'] and not user.is_active:
            user.is_active = True
            update_fields.append('is_active')
        user.save(update_fields=update_fields)
        self.stdout.write(
            self.style.SUCCESS(
                f'{user.email}: papel definido como '
                f'{user.get_role_display()}.'
            )
        )

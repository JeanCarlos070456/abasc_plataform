from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.associates.models import Payment
from apps.core.models import SiteConfiguration
from apps.news.models import Category, Post

class Command(BaseCommand):
    help = 'Cria dados demonstrativos do ABASC MVP 1.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                'O seed demonstrativo só pode ser executado com DEBUG=True.'
            )

        SiteConfiguration.objects.update_or_create(
            pk=1,
            defaults={
                'site_name': 'ABASC',
                'full_name': (
                    'Associação de Bacharéis em Saúde Coletiva'
                ),
                'contact_email': 'abasc.comunica@gmail.com',
            },
        )

        users = [
            (
                'presidente@abasc.demo',
                'Presidência',
                'ABASC',
                User.Role.PRESIDENT,
                User.AssociationStatus.ACTIVE,
                'ABASC-0001',
            ),
            (
                'executivo@abasc.demo',
                'Executivo',
                'ABASC',
                User.Role.EXECUTIVE,
                User.AssociationStatus.ACTIVE,
                'ABASC-0002',
            ),
            (
                'associado@abasc.demo',
                'Associado',
                'Demonstração',
                User.Role.ASSOCIATE,
                User.AssociationStatus.ACTIVE,
                'ABASC-0100',
            ),
        ]
        created_users = {}
        for email, first, last, role, status, number in users:
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={'username': email},
            )
            user.username = email
            user.first_name = first
            user.last_name = last
            user.role = role
            user.association_status = status
            user.membership_number = number
            user.is_active = True
            user.set_password('Abasc@123')
            user.save()
            created_users[role] = user

        categories_data = [
            (
                'Notícias institucionais',
                'Comunicados e atualizações oficiais da ABASC.',
            ),
            (
                'Regulamentação',
                'Projetos de lei, normas e avanços profissionais.',
            ),
            (
                'Eventos',
                'Congressos, assembleias, reuniões e encontros.',
            ),
            (
                'Oportunidades',
                'Processos seletivos, vagas, cursos e bolsas.',
            ),
        ]
        categories = {}
        for name, description in categories_data:
            category, _ = Category.objects.get_or_create(
                name=name,
                defaults={'description': description},
            )
            categories[name] = category

        posts = [
            {
                'title': (
                    'ABASC apresenta a nova plataforma digital '
                    'para associados'
                ),
                'summary': (
                    'O novo ambiente reúne notícias, dados associativos, '
                    'pagamentos e painéis gerenciais em uma única plataforma.'
                ),
                'body': (
                    'A ABASC inicia uma nova etapa de transformação digital. '
                    'A plataforma foi planejada para aproximar associados, '
                    'executivos e presidência, com acesso seguro e '
                    'comunicação institucional centralizada.'
                ),
                'category': categories['Notícias institucionais'],
                'featured': True,
            },
            {
                'title': (
                    'Regulamentação da profissão de sanitarista '
                    'avança no debate nacional'
                ),
                'summary': (
                    'A Associação acompanha e apoia iniciativas voltadas '
                    'ao reconhecimento e fortalecimento da atuação profissional.'
                ),
                'body': (
                    'A regulamentação profissional permanece entre as pautas '
                    'estratégicas da ABASC. A plataforma divulgará '
                    'atualizações, documentos e mobilizações relacionadas.'
                ),
                'category': categories['Regulamentação'],
            },
            {
                'title': 'Agenda de encontros e assembleias da ABASC',
                'summary': (
                    'Consulte as próximas atividades institucionais e '
                    'acompanhe os comunicados destinados aos associados.'
                ),
                'body': (
                    'As agendas e convocações oficiais serão disponibilizadas '
                    'neste espaço. Conteúdos restritos serão exibidos somente '
                    'após autenticação.'
                ),
                'category': categories['Eventos'],
                'visibility': Post.Visibility.ASSOCIATES,
            },
            {
                'title': (
                    'Oportunidade: seleção para projeto em Saúde Coletiva'
                ),
                'summary': (
                    'Publicação demonstrativa de processo seletivo com '
                    'link externo, imagem e resumo objetivo.'
                ),
                'body': (
                    'Este conteúdo demonstra o fluxo de oportunidades. '
                    'O executivo pode cadastrar texto, imagem e endereço '
                    'externo sem alterar o código do sistema.'
                ),
                'category': categories['Oportunidades'],
                'is_opportunity': True,
                'external_url': 'https://example.org/oportunidade',
            },
        ]
        for item in posts:
            Post.objects.get_or_create(
                title=item['title'],
                defaults={
                    'summary': item['summary'],
                    'body': item['body'],
                    'category': item['category'],
                    'author': created_users[User.Role.EXECUTIVE],
                    'status': Post.Status.PUBLISHED,
                    'visibility': item.get(
                        'visibility',
                        Post.Visibility.PUBLIC,
                    ),
                    'featured': item.get('featured', False),
                    'is_opportunity': item.get(
                        'is_opportunity',
                        False,
                    ),
                    'external_url': item.get('external_url', ''),
                    'published_at': timezone.now(),
                },
            )

        associate = created_users[User.Role.ASSOCIATE]
        today = date.today()
        first_this_month = today.replace(day=1)
        previous_month_end = first_this_month - timedelta(days=1)
        previous_month = previous_month_end.replace(day=1)
        next_month = (
            first_this_month.replace(day=28) + timedelta(days=4)
        ).replace(day=1)

        Payment.objects.update_or_create(
            associate=associate,
            reference_month=previous_month,
            defaults={
                'due_date': previous_month.replace(day=10),
                'paid_at': previous_month.replace(day=8),
                'amount': Decimal('50.00'),
                'status': Payment.Status.PAID,
            },
        )
        Payment.objects.update_or_create(
            associate=associate,
            reference_month=next_month,
            defaults={
                'due_date': next_month.replace(day=10),
                'amount': Decimal('50.00'),
                'status': Payment.Status.PENDING,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                'Dados demonstrativos criados ou atualizados.'
            )
        )
        self.stdout.write(
            'Presidente: presidente@abasc.demo / Abasc@123'
        )
        self.stdout.write(
            'Executivo: executivo@abasc.demo / Abasc@123'
        )
        self.stdout.write(
            'Associado: associado@abasc.demo / Abasc@123'
        )

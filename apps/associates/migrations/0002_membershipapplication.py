from django.conf import settings
from django.db import migrations, models
import uuid
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("associates", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MembershipApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="identificador público")),
                ("status", models.CharField(choices=[("pending", "Pendente"), ("approved", "Aprovada")], db_index=True, default="pending", max_length=20, verbose_name="status")),
                ("application_type", models.CharField(choices=[("new", "Nova associação"), ("renewal", "Renovação da associação")], max_length=20, verbose_name="tipo de solicitação")),
                ("category", models.CharField(choices=[("junior", "Associado Júnior"), ("full", "Associado Pleno")], max_length=20, verbose_name="categoria")),
                ("consent_statute", models.BooleanField(verbose_name="aceitou o estatuto")),
                ("consent_research", models.BooleanField(blank=True, default=False, verbose_name="autoriza convites para pesquisas")),
                ("consent_communications", models.BooleanField(blank=True, default=False, verbose_name="autoriza comunicações da ABASC")),
                ("truth_declaration", models.BooleanField(verbose_name="declarou a veracidade das informações")),
                ("payment_agreement", models.BooleanField(verbose_name="concordou com o pagamento via PIX")),
                ("full_name", models.CharField(max_length=180, verbose_name="nome completo")),
                ("email", models.EmailField(max_length=254, verbose_name="e-mail")),
                ("cpf", models.CharField(max_length=14, verbose_name="CPF")),
                ("birth_date", models.DateField(verbose_name="data de nascimento")),
                ("gender", models.CharField(choices=[("female", "Feminino"), ("male", "Masculino"), ("non_binary", "Não binário")], max_length=20, verbose_name="gênero")),
                ("race_ethnicity", models.CharField(choices=[("yellow", "Amarela"), ("white", "Branca"), ("indigenous", "Indígena"), ("brown", "Parda"), ("black", "Preta")], max_length=20, verbose_name="cor, raça e etnia")),
                ("has_disability", models.CharField(choices=[("yes", "Sim"), ("no", "Não")], max_length=3, verbose_name="possui alguma deficiência")),
                ("disability_description", models.CharField(blank=True, max_length=255, verbose_name="descrição da deficiência")),
                ("marital_status", models.CharField(choices=[("single", "Solteiro(a)"), ("married", "Casado(a)"), ("divorced", "Divorciado(a)"), ("widowed", "Viúvo(a)"), ("legally_separated", "Separado(a) judicialmente"), ("stable_union", "União estável")], max_length=30, verbose_name="estado civil")),
                ("university", models.CharField(max_length=180, verbose_name="universidade")),
                ("health_collective_link", models.TextField(max_length=1000, verbose_name="vínculo com a Saúde Coletiva")),
                ("state", models.CharField(choices=[("AC", "Acre"), ("AL", "Alagoas"), ("AP", "Amapá"), ("AM", "Amazonas"), ("BA", "Bahia"), ("CE", "Ceará"), ("DF", "Distrito Federal"), ("ES", "Espírito Santo"), ("GO", "Goiás"), ("MA", "Maranhão"), ("MT", "Mato Grosso"), ("MS", "Mato Grosso do Sul"), ("MG", "Minas Gerais"), ("PA", "Pará"), ("PB", "Paraíba"), ("PR", "Paraná"), ("PE", "Pernambuco"), ("PI", "Piauí"), ("RJ", "Rio de Janeiro"), ("RN", "Rio Grande do Norte"), ("RS", "Rio Grande do Sul"), ("RO", "Rondônia"), ("RR", "Roraima"), ("SC", "Santa Catarina"), ("SP", "São Paulo"), ("SE", "Sergipe"), ("TO", "Tocantins")], max_length=2, verbose_name="UF")),
                ("city", models.CharField(max_length=120, verbose_name="município")),
                ("whatsapp", models.CharField(max_length=20, verbose_name="WhatsApp")),
                ("allow_whatsapp_group", models.CharField(choices=[("yes", "Sim"), ("no", "Não")], max_length=3, verbose_name="aceita participar do grupo de WhatsApp")),
                ("lattes_url", models.URLField(blank=True, verbose_name="Currículo Lattes")),
                ("instagram", models.CharField(blank=True, max_length=100, verbose_name="Instagram")),
                ("supporting_document_path", models.CharField(max_length=500, verbose_name="caminho da documentação")),
                ("supporting_document_name", models.CharField(max_length=255, verbose_name="nome da documentação")),
                ("supporting_document_content_type", models.CharField(max_length=100, verbose_name="tipo da documentação")),
                ("supporting_document_size", models.PositiveBigIntegerField(verbose_name="tamanho da documentação")),
                ("payment_receipt_path", models.CharField(max_length=500, verbose_name="caminho do comprovante")),
                ("payment_receipt_name", models.CharField(max_length=255, verbose_name="nome do comprovante")),
                ("payment_receipt_content_type", models.CharField(max_length=100, verbose_name="tipo do comprovante")),
                ("payment_receipt_size", models.PositiveBigIntegerField(verbose_name="tamanho do comprovante")),
                ("requested_at", models.DateTimeField(auto_now_add=True, verbose_name="solicitado em")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True, verbose_name="analisado em")),
                ("decision_notes", models.TextField(blank=True, verbose_name="observações da análise")),
                ("approved_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approved_membership_applications", to=settings.AUTH_USER_MODEL, verbose_name="usuário aprovado")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_membership_applications", to=settings.AUTH_USER_MODEL, verbose_name="analisado por")),
            ],
            options={
                "verbose_name": "solicitação de associação",
                "verbose_name_plural": "solicitações de associação",
                "ordering": ["-requested_at"],
            },
        ),
        migrations.AddIndex(
            model_name="membershipapplication",
            index=models.Index(fields=["status", "-requested_at"], name="assoc_app_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="membershipapplication",
            index=models.Index(fields=["email", "status"], name="assoc_app_email_status_idx"),
        ),
        migrations.AddIndex(
            model_name="membershipapplication",
            index=models.Index(fields=["cpf", "status"], name="assoc_app_cpf_status_idx"),
        ),
    ]
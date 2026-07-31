from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PAID = "paid", "Pago"
        OVERDUE = "overdue", "Vencido"
        CANCELED = "canceled", "Cancelado"

    associate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="associado",
    )
    reference_month = models.DateField(
        "mês de referência",
        help_text="Use o primeiro dia do mês.",
    )
    due_date = models.DateField("vencimento")
    paid_at = models.DateField(
        "data do pagamento",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(
        "valor",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    status = models.CharField(
        "status",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    notes = models.CharField(
        "observações",
        max_length=255,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "pagamento"
        verbose_name_plural = "pagamentos"
        ordering = ["-reference_month"]
        constraints = [
            models.UniqueConstraint(
                fields=["associate", "reference_month"],
                name="uniq_assoc_reference_month",
            )
        ]
        indexes = [
            models.Index(
                fields=["status", "due_date"],
                name="assoc_pay_status_due_idx",
            ),
            models.Index(
                fields=["associate", "-reference_month"],
                name="assoc_pay_user_ref_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.status == self.Status.PAID and not self.paid_at:
            raise ValidationError({
                "paid_at": "Informe a data do pagamento para um registro pago."
            })

    def save(self, *args, **kwargs):
        if self.reference_month:
            self.reference_month = self.reference_month.replace(day=1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.associate} — {self.reference_month:%m/%Y}"


class MembershipApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        APPROVED = "approved", "Aprovada"

    class ApplicationType(models.TextChoices):
        NEW = "new", "Nova associação"
        RENEWAL = "renewal", "Renovação da associação"

    class Category(models.TextChoices):
        JUNIOR = "junior", "Associado Júnior"
        FULL = "full", "Associado Pleno"

    class Gender(models.TextChoices):
        FEMALE = "female", "Feminino"
        MALE = "male", "Masculino"
        NON_BINARY = "non_binary", "Não binário"

    class RaceEthnicity(models.TextChoices):
        YELLOW = "yellow", "Amarela"
        WHITE = "white", "Branca"
        INDIGENOUS = "indigenous", "Indígena"
        BROWN = "brown", "Parda"
        BLACK = "black", "Preta"

    class YesNo(models.TextChoices):
        YES = "yes", "Sim"
        NO = "no", "Não"

    class MaritalStatus(models.TextChoices):
        SINGLE = "single", "Solteiro(a)"
        MARRIED = "married", "Casado(a)"
        DIVORCED = "divorced", "Divorciado(a)"
        WIDOWED = "widowed", "Viúvo(a)"
        LEGALLY_SEPARATED = "legally_separated", "Separado(a) judicialmente"
        STABLE_UNION = "stable_union", "União estável"

    UF_CHOICES = [
        ("AC", "Acre"), ("AL", "Alagoas"), ("AP", "Amapá"),
        ("AM", "Amazonas"), ("BA", "Bahia"), ("CE", "Ceará"),
        ("DF", "Distrito Federal"), ("ES", "Espírito Santo"),
        ("GO", "Goiás"), ("MA", "Maranhão"), ("MT", "Mato Grosso"),
        ("MS", "Mato Grosso do Sul"), ("MG", "Minas Gerais"),
        ("PA", "Pará"), ("PB", "Paraíba"), ("PR", "Paraná"),
        ("PE", "Pernambuco"), ("PI", "Piauí"),
        ("RJ", "Rio de Janeiro"), ("RN", "Rio Grande do Norte"),
        ("RS", "Rio Grande do Sul"), ("RO", "Rondônia"),
        ("RR", "Roraima"), ("SC", "Santa Catarina"),
        ("SP", "São Paulo"), ("SE", "Sergipe"), ("TO", "Tocantins"),
    ]

    public_id = models.UUIDField(
        "identificador público",
        default=uuid4,
        unique=True,
        editable=False,
    )
    status = models.CharField(
        "status",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    application_type = models.CharField(
        "tipo de solicitação",
        max_length=20,
        choices=ApplicationType.choices,
    )
    category = models.CharField(
        "categoria",
        max_length=20,
        choices=Category.choices,
    )

    consent_statute = models.BooleanField("aceitou o estatuto")
    consent_research = models.BooleanField(
        "autoriza convites para pesquisas",
        default=False,
        blank=True,
    )
    consent_communications = models.BooleanField(
        "autoriza comunicações da ABASC",
        default=False,
        blank=True,
    )
    truth_declaration = models.BooleanField(
        "declarou a veracidade das informações"
    )
    payment_agreement = models.BooleanField(
        "concordou com o pagamento via PIX"
    )

    full_name = models.CharField("nome completo", max_length=180)
    email = models.EmailField("e-mail", max_length=254)
    cpf = models.CharField("CPF", max_length=14)
    birth_date = models.DateField("data de nascimento")
    gender = models.CharField(
        "gênero",
        max_length=20,
        choices=Gender.choices,
    )
    race_ethnicity = models.CharField(
        "cor, raça e etnia",
        max_length=20,
        choices=RaceEthnicity.choices,
    )
    has_disability = models.CharField(
        "possui alguma deficiência",
        max_length=3,
        choices=YesNo.choices,
    )
    disability_description = models.CharField(
        "descrição da deficiência",
        max_length=255,
        blank=True,
    )
    marital_status = models.CharField(
        "estado civil",
        max_length=30,
        choices=MaritalStatus.choices,
    )

    university = models.CharField("universidade", max_length=180)
    health_collective_link = models.TextField(
        "vínculo com a Saúde Coletiva",
        max_length=1000,
    )
    state = models.CharField("UF", max_length=2, choices=UF_CHOICES)
    city = models.CharField("município", max_length=120)
    whatsapp = models.CharField("WhatsApp", max_length=20)
    allow_whatsapp_group = models.CharField(
        "aceita participar do grupo de WhatsApp",
        max_length=3,
        choices=YesNo.choices,
    )
    lattes_url = models.URLField("Currículo Lattes", blank=True)
    instagram = models.CharField("Instagram", max_length=100, blank=True)

    supporting_document_path = models.CharField(
        "caminho da documentação",
        max_length=500,
    )
    supporting_document_name = models.CharField(
        "nome da documentação",
        max_length=255,
    )
    supporting_document_content_type = models.CharField(
        "tipo da documentação",
        max_length=100,
    )
    supporting_document_size = models.PositiveBigIntegerField(
        "tamanho da documentação"
    )

    payment_receipt_path = models.CharField(
        "caminho do comprovante",
        max_length=500,
    )
    payment_receipt_name = models.CharField(
        "nome do comprovante",
        max_length=255,
    )
    payment_receipt_content_type = models.CharField(
        "tipo do comprovante",
        max_length=100,
    )
    payment_receipt_size = models.PositiveBigIntegerField(
        "tamanho do comprovante"
    )

    requested_at = models.DateTimeField("solicitado em", auto_now_add=True)
    reviewed_at = models.DateTimeField("analisado em", null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_membership_applications",
        null=True,
        blank=True,
        verbose_name="analisado por",
    )
    approved_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_membership_applications",
        null=True,
        blank=True,
        verbose_name="usuário aprovado",
    )
    decision_notes = models.TextField("observações da análise", blank=True)

    class Meta:
        verbose_name = "solicitação de associação"
        verbose_name_plural = "solicitações de associação"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(
                fields=["status", "-requested_at"],
                name="assoc_app_status_created_idx",
            ),
            models.Index(
                fields=["email", "status"],
                name="assoc_app_email_status_idx",
            ),
            models.Index(
                fields=["cpf", "status"],
                name="assoc_app_cpf_status_idx",
            ),
        ]

    @property
    def amount(self):
        if self.category == self.Category.JUNIOR:
            return Decimal("50.00")
        return Decimal("100.00")

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    def clean(self):
        super().clean()
        if not self.consent_statute:
            raise ValidationError({
                "consent_statute": "É necessário aceitar o estatuto da ABASC."
            })
        if not self.truth_declaration:
            raise ValidationError({
                "truth_declaration": "É necessário confirmar a veracidade das informações."
            })
        if not self.payment_agreement:
            raise ValidationError({
                "payment_agreement": "É necessário concordar com o pagamento via PIX."
            })
        if self.has_disability == self.YesNo.YES and not self.disability_description:
            raise ValidationError({
                "disability_description": "Descreva a deficiência informada."
            })

    def __str__(self):
        return f"{self.full_name} — {self.get_status_display()}"
from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class CustomUser(AbstractUser):
    NIVEL_ACESSO_CHOICES = [
        ('ADMIN', 'Administrador'),
        ('GESTOR', 'Gestor'),
        ('OPERADOR', 'Operador'),
        ('VISUALIZADOR', 'Visualizador'),
    ]

    telefone = models.CharField(max_length=15, blank=True, null=True)
    nivel_acesso = models.CharField(max_length=20, choices=NIVEL_ACESSO_CHOICES, default='OPERADOR')
    sector = models.ForeignKey(
        'Sector',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios'
    )
    data_registro = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.username} - {self.get_nivel_acesso_display()}"
    

# <----- Modelo para Autocarro -----> #
class Motorista(models.Model):
    nome = models.CharField(max_length=120)
    telefone = models.CharField(max_length=30, blank=True, null=True)
    numero_bi = models.CharField(max_length=50, blank=True, null=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


# Status choices para Autocarro
STATUS_CHOICES = [
    ("ativo", "Ativo"),
    ("manutencao", "Em manutenção"),
    ("inativo", "Inativo"),
]


class Autocarro(models.Model):
    numero = models.CharField(max_length=20, unique=True, verbose_name="Número do Autocarro")
    modelo = models.CharField(max_length=100, verbose_name="Modelo")
    placa = models.CharField(max_length=20, verbose_name="Placa")
    sector = models.ForeignKey("Sector", on_delete=models.CASCADE, related_name="autocarros")

    # 🔹 coordenadas fixas para simulação
    lat = models.FloatField(default=-8.8383)
    lng = models.FloatField(default=13.2344)

    # 🔹 campo status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ativo")

    def __str__(self):
        return f"Autocarro {self.numero} - {self.sector.nome}"


class EstadoAutocarro(models.Model):
    autocarro = models.ForeignKey(Autocarro, on_delete=models.CASCADE, related_name="estados")
    data = models.DateTimeField(auto_now_add=True)

    # Estado geral
    motor_funciona = models.BooleanField(default=True)
    pneus_bons = models.BooleanField(default=True)
    luzes_funcionam = models.BooleanField(default=True)
    travoes_bons = models.BooleanField(default=True)
    parabrisas_ok = models.BooleanField(default=True)
    bancos_bons = models.BooleanField(default=True)

    observacoes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Estado {self.autocarro.numero} em {self.data}"


# <----- Modelo de registo diário de viagens por Região -----> #
class Sector(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    gestor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sectores_geridos"
    )
    associados = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="sectores_associados"
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            slug = slugify(self.nome)
            i = 1
            while Sector.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{slug}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome



class RelatorioSector(models.Model):
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name='relatorios')
    data = models.DateField()
    descricao = models.TextField(blank=True, null=True)
    
    # 🔹 REMOVIDO: comprovativo singular (agora usamos múltiplos comprovativos)
    # comprovativo = models.FileField(upload_to='comprovativos/', null=True, blank=True)

    class Meta:
        unique_together = ['sector', 'data']  # 🔹 IMPEDE MÚLTIPLOS RELATÓRIOS POR DIA
        ordering = ['-data']

    def clean(self):
        """Validação para evitar relatórios duplicados"""
        if RelatorioSector.objects.filter(
            sector=self.sector, 
            data=self.data
        ).exclude(pk=self.pk).exists():
            raise ValidationError(f"Já existe um relatório para o sector {self.sector.nome} na data {self.data}")

    def __str__(self):
        return f"Relatório {self.sector.nome} - {self.data}"


# 🔹 NOVO MODELO PARA MÚLTIPLOS COMPROVATIVOS
class ComprovativoRelatorio(models.Model):
    relatorio = models.ForeignKey(RelatorioSector, on_delete=models.CASCADE, related_name='comprovativos')
    arquivo = models.FileField(upload_to='comprovativos/relatorios/')
    descricao = models.CharField(max_length=255, blank=True, null=True)
    enviado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comprovativo {self.id} - {self.relatorio}"

    class Meta:
        ordering = ['-enviado_em']


# <----- Modelo de registo diário de viagens por autocarro -----> #
class RegistoDiario(models.Model):
    def save(self, *args, **kwargs):
        # Calcula o número de passageiros automaticamente usando a fórmula:
        # (normal + alunos)/200 + (luvu + frete)/1000
        try:
            # garantir que estamos a usar Decimal para precisão
            normal = Decimal(self.normal or 0)
            alunos = Decimal(self.alunos or 0)
            luvu = Decimal(self.luvu or 0)
            frete = Decimal(self.frete or 0)
            passageiros = ( (normal + alunos) / Decimal('200') ) + ( (luvu + frete) / Decimal('1000') )
            # usar int() (truncar) para manter comportamento semelhante ao Math.floor
            self.numero_passageiros = int(passageiros)
        except Exception:
            self.numero_passageiros = 0
        super().save(*args, **kwargs)
    autocarro = models.ForeignKey('Autocarro', on_delete=models.CASCADE, related_name='registos_diarios')
    relatorio = models.ForeignKey('RelatorioSector', on_delete=models.CASCADE, related_name='registos', null=True, blank=True)
    data = models.DateField(default=timezone.now, verbose_name="Data")
    
    # Status fields
    concluido = models.BooleanField(default=False)
    validado = models.BooleanField(default=False)
    data_conclusao = models.DateTimeField(null=True, blank=True)
    data_validacao = models.DateTimeField(null=True, blank=True)
    
    # Campos financeiros
    normal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    alunos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    luvu = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    frete = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    alimentacao = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    parqueamento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taxa = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    outros = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    numero_passageiros = models.PositiveIntegerField(default=0)
    numero_viagens = models.PositiveIntegerField(default=0)
    km_percorridos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    motorista = models.CharField(max_length=100, blank=True, default="N/A")
    cobrador_principal = models.CharField(max_length=100, blank=True, default="N/A")
    cobrador_auxiliar = models.CharField(max_length=100, blank=True, default="N/A")

    class Meta:
        unique_together = ['autocarro', 'data']
        verbose_name_plural = "Registos Diários"

    def entradas_total(self):
        return self.normal + self.alunos + self.luvu + self.frete

    def saidas_total(self):
        return self.alimentacao + self.parqueamento + self.taxa + self.outros

    def saldo_liquido(self):
        return self.entradas_total() - self.saidas_total()

    def clean(self):
        if self.autocarro_id and self.data:
            qs = RegistoDiario.objects.filter(autocarro=self.autocarro, data=self.data)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(f"Já existe um registo para este autocarro na data {self.data}")

    def __str__(self):
        return f"{self.autocarro.numero} - {self.data}"



# <----- Arquivos anexados ao registo -----> #
class RegistoArquivo(models.Model):
    registo = models.ForeignKey(RegistoDiario, on_delete=models.CASCADE, related_name="arquivos")
    arquivo = models.FileField(upload_to="registos/arquivos/")
    descricao = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Arquivo {self.id} - {self.registo}"



# <----- Modelo para Despesa -----> #
class Despesa(models.Model):
    registo = models.ForeignKey(RegistoDiario, on_delete=models.CASCADE, related_name='despesas', null=True, blank=True)
    # opcional: associar despesa a um sector (ou NULL para despesa geral)
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, related_name='despesas', null=True, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.TextField()
    data = models.DateField()
    numero_transacao = models.CharField(max_length=50, blank=True, null=True)
    numero_requisicao = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.descricao} - {self.valor}"



class DespesaCombustivel(models.Model):
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE)
    autocarro = models.ForeignKey(Autocarro, on_delete=models.CASCADE)
    data = models.DateField(default=timezone.now)
    valor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valor_litros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    comprovativo = models.FileField(upload_to="comprovativos/combustivel/", null=True, blank=True)
    descricao = models.TextField(null=True, blank=True)
    sobragem_filtros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    lavagem = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    @property
    def litros(self):
        if self.valor_litros and self.valor_litros > 0:
            return self.valor / self.valor_litros
        return 0

    def __str__(self):
        return f"Combustível {self.autocarro.numero} - {self.valor}Kz"



# <----- Arquivos comprovativos de despesas -----> #
class Comprovativo(models.Model):
    despesa = models.ForeignKey(Despesa, on_delete=models.CASCADE, related_name="comprovativos")
    arquivo = models.FileField(upload_to="despesas/comprovativos/")
    enviado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comprovativo de {self.despesa.descricao}"

    class Meta:
        ordering = ['-enviado_em']


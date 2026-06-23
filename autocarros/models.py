from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission

class CustomUser(AbstractUser):
    NIVEL_ACESSO_CHOICES = [
        ('admin', 'Administrador'),
        ('gestor', 'Gestor'),
        ('user', 'Usuário'),
    ]

    telefone = models.CharField(max_length=15, blank=True, null=True)
    nivel_acesso = models.CharField(
        max_length=20, 
        choices=NIVEL_ACESSO_CHOICES, 
        default='user'
    )
    ativo = models.BooleanField(default=True)

    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',
        related_query_name='customuser',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_set',
        related_query_name='customuser',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return self.username

    

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

    despesa_geral = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Despesa geral do setor"
    )

    alimentacao_estaleiro = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Despesa com alimentação do estaleiro"
    )

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
        try:
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
    taxi = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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
        return self.alimentacao + self.parqueamento + self.taxa + self.outros + self.taxi

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


class DespesaFixa(models.Model):
    CATEGORIAS = [
        ('salario', 'Salários'),
        ('fundo_maneio', 'Fundo De Maneio'),
        ('subsidio_alimentacao', 'Subsídio de Alimentação'),
        ('cameras', 'Carregamento das Câmaras'),
        ('gps', 'Carregamento de GPS'),
        ('internet_tv', 'Internet/TV do Escritório'),
        ('agua_luz', 'Água e Luz'),
        ('prestacao', 'Prestação dos Autocarros'),
        ('seguro', 'Seguro das Viaturas'),
        ('outro', 'Outro'),
    ]

    sector = models.ForeignKey('Sector', on_delete=models.CASCADE, related_name='despesas_fixas')
    categoria = models.CharField(max_length=32, choices=CATEGORIAS)
    descricao = models.CharField(max_length=255, blank=True)
    valor = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    periodicidade = models.CharField(max_length=32, default='mensal', help_text='mensal|anual|único')
    ativo = models.BooleanField(default=True)
    data_inicio = models.DateField(null=True, blank=True)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Despesa Fixa'
        verbose_name_plural = 'Despesas Fixas'
        ordering = ['-ativo', 'sector', 'categoria']

    def __str__(self):
        return f"{self.get_categoria_display()} — {self.sector.nome} — {self.valor:.2f}"


# <----- Arquivos comprovativos de despesas -----> #
class Comprovativo(models.Model):
    despesa = models.ForeignKey(Despesa, on_delete=models.CASCADE, related_name="comprovativos")
    arquivo = models.FileField(upload_to="despesas/comprovativos/")
    enviado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comprovativo de {self.despesa.descricao}"

    class Meta:
        ordering = ['-enviado_em']


class Deposito(models.Model):
    sector = models.ForeignKey('Sector', on_delete=models.CASCADE, related_name='depositos')
    data_deposito = models.DateField(default=timezone.localdate)
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    observacao = models.TextField(blank=True, null=True)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='depositos_responsavel')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_deposito', '-criado_em']

    def __str__(self):
        return f"Depósito {self.sector.nome} {self.data_deposito} — {self.valor}"



class CobradorViagem(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('approved', 'Aprovada'),
        ('rejected', 'Rejeitada'),
    ]

    autocarro = models.ForeignKey('Autocarro', on_delete=models.CASCADE, related_name='viagens_cobrador')
    cobrador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    data = models.DateField()
    hora = models.TimeField(null=True, blank=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    passageiros = models.PositiveIntegerField(default=0)
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    # Validação / auditoria
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    validado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='viagens_validas')
    validado_em = models.DateTimeField(null=True, blank=True)
    nota_validacao = models.TextField(blank=True, null=True)
    valor_aprovado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-data', '-hora', '-criado_em']

    def __str__(self):
        return f"Viagem {self.autocarro} {self.data} {self.hora} — {self.valor}"

    def approve(self, user, valor_aprovado=None, nota=None):
        from django.utils import timezone
        self.status = 'approved'
        self.validado_por = user
        self.validado_em = timezone.now()
        if valor_aprovado is not None:
            self.valor_aprovado = Decimal(valor_aprovado)
        if nota:
            self.nota_validacao = nota
        self.save(update_fields=['status', 'validado_por', 'validado_em', 'valor_aprovado', 'nota_validacao'])

    def reject(self, user, nota=None):
        from django.utils import timezone
        self.status = 'rejected'
        self.validado_por = user
        self.validado_em = timezone.now()
        if nota:
            self.nota_validacao = nota
        self.save(update_fields=['status', 'validado_por', 'validado_em', 'nota_validacao'])


# <----- Modelo para Manutenção de Autocarros -----> #

from django.db import models
from django.conf import settings
from decimal import Decimal

class Manutencao(models.Model):
    STATUS_CHOICES = [
        ('agendada', 'Agendada'),
        ('em_progresso', 'Em Progresso'),
        ('concluida', 'Concluída'),
        ('cancelada', 'Cancelada'),
    ]

    sector = models.ForeignKey('Sector', on_delete=models.CASCADE, related_name='manutencoes')
    autocarro = models.ForeignKey('Autocarro', on_delete=models.CASCADE, related_name='manutencoes')
    data_ultima = models.DateField(help_text='Data da última manutenção realizada')

    # 🔹 Alterados para DecimalField
    km_ultima = models.DecimalField(max_digits=14, decimal_places=2, help_text='Km na última manutenção')
    km_proxima = models.DecimalField(max_digits=14, decimal_places=2, help_text='Km previsto para próxima manutenção')

    # substituições (sim/não)
    oleo_motor = models.BooleanField(default=False)
    oleo_diferencial = models.BooleanField(default=False)
    oleo_cambio = models.BooleanField(default=False)
    filtro_combustivel = models.BooleanField(default=False)
    filtro_oleo = models.BooleanField(default=False)
    filtro_ar = models.BooleanField(default=False)

    # ---> novos campos: km previstos para cada item <---
    km_prox_oleo_motor = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text='Km previsto para próxima troca do óleo do motor')
    km_prox_oleo_diferencial = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text='Km previsto para próxima troca do óleo do diferencial')
    km_prox_oleo_cambio = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text='Km previsto para próxima troca do óleo do câmbio')
    km_prox_filtro_combustivel = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text='Km previsto para troca do filtro de combustível')
    km_prox_filtro_oleo = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text='Km previsto para troca do filtro de óleo')
    km_prox_filtro_ar = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text='Km previsto para troca do filtro de ar')

    custo_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    observacao = models.TextField(blank=True, null=True)

    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='manutencoes_responsavel'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='agendada')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        try:
            if (not getattr(self, 'km_proxima', None)) and (getattr(self, 'km_ultima', None) is not None):
                base_km = Decimal(self.km_ultima)
                self.km_proxima = base_km + Decimal('4500.00')
                self.km_prox_oleo_motor = base_km + Decimal('7000.00')
                self.km_prox_oleo_diferencial = base_km + Decimal('5000.00')
                self.km_prox_oleo_cambio = base_km + Decimal('10000.00')
                self.km_prox_filtro_combustivel = base_km + Decimal('7000.00')
                self.km_prox_filtro_oleo = base_km + Decimal('7000.00')
                self.km_prox_filtro_ar = base_km + Decimal('7000.00')
        except Exception:
            pass
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-data_ultima', '-criado_em']

    def __str__(self):
        return f"Manut. {self.autocarro.numero} {self.data_ultima} — {self.get_status_display()}"


class RegistroKM(models.Model):
    sector = models.ForeignKey('Sector', on_delete=models.CASCADE, related_name='registros_km')
    data_registo = models.DateField(default=timezone.localdate)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RegistroKM {self.sector.nome} {self.data_registo}"

class RegistroKMItem(models.Model):
    registro = models.ForeignKey(RegistroKM, on_delete=models.CASCADE, related_name='itens')
    autocarro = models.ForeignKey('Autocarro', on_delete=models.CASCADE, related_name='+')
    km_atual = models.PositiveIntegerField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('registro', 'autocarro')

    def __str__(self):
        return f"{self.autocarro.numero} — {self.km_atual}"


# <----- Modelo para Categoria de Despesa -----> #
from django.db import models

class CategoriaDespesa(models.Model):
    TIPO_CHOICES = (
        ('FIXA', 'Despesa Fixa'),
        ('VARIAVEL', 'Despesa Variável'),
    )

    nome = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        unique=True
    )

    ativa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoria de Despesa"
        verbose_name_plural = "Categorias de Despesa"

    def __str__(self):
        return self.get_nome_display()

# <----- Modelo para Subcategoria de Despesa -----> #
class SubCategoriaDespesa(models.Model):
    categoria = models.ForeignKey(
        CategoriaDespesa,
        on_delete=models.PROTECT,
        related_name='subcategorias'
    )

    nome = models.CharField(max_length=100)
    ativa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Subcategoria de Despesa"
        verbose_name_plural = "Subcategorias de Despesa"
        unique_together = ('categoria', 'nome')
        ordering = ['categoria', 'nome']

    def __str__(self):
        return f"{self.nome} ({self.categoria})"

# <----- Modelo para Despesa -----> #
class Despesa2(models.Model):
    categoria = models.ForeignKey(
        CategoriaDespesa,
        on_delete=models.PROTECT
    )

    subcategoria = models.ForeignKey(
        SubCategoriaDespesa,
        on_delete=models.PROTECT,
        related_name='despesas'
    )

    data = models.DateField()
    valor = models.DecimalField(max_digits=14, decimal_places=2)

    descricao = models.CharField(max_length=255, blank=True)
    observacao = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Despesa"
        verbose_name_plural = "Despesas"
        ordering = ['-data']

    from django.core.exceptions import ValidationError

    def clean(self):
        super().clean()

        if not self.subcategoria or not self.categoria:
            return

        if self.subcategoria.categoria != self.categoria:
            raise ValidationError(
                {"subcategoria": "A subcategoria não pertence à categoria selecionada."}
            )

    def __str__(self):
        return f"{self.data} - {self.subcategoria.nome} - {self.valor}"


# ═══════════════════════════════════════════════════════════
# 3. CONTABILIDA & FINANÇAS
# ═══════════════════════════════════════════════════════════


from django.db import models
from django.core.exceptions import ValidationError
from mptt.models import MPTTModel, TreeForeignKey


class PlanoContas(MPTTModel):
    """
    Plano de Contas dinâmico e hierárquico (Classe > Subclasse > Conta > Subconta).

    O utilizador (contabilista/gestor) define livremente a estrutura pela
    interface. O sistema só garante 3 regras mínimas para não deixar o plano
    "quebrar" — não é preciso ser especialista em contabilidade para usar isto.
    """

    TIPO_CHOICES = [
        ('S', 'Sintética (agrupadora — soma as filhas)'),
        ('A', 'Analítica (recebe lançamentos)'),
    ]

    NATUREZA_CHOICES = [
        ('D', 'Devedora'),   # Ativos, Gastos
        ('C', 'Credora'),    # Passivos, Capital Próprio, Rendimentos
    ]

    codigo = models.CharField('Código', max_length=20, unique=True)
    nome = models.CharField('Designação', max_length=150)
    tipo = models.CharField('Tipo', max_length=1, choices=TIPO_CHOICES, default='A')
    natureza = models.CharField('Natureza', max_length=1, choices=NATUREZA_CHOICES)
    ativo = models.BooleanField('Ativa', default=True)
    permite_lancamento = models.BooleanField(
        'Permite lançamento direto', default=True,
        help_text='É desligado automaticamente para contas Sintéticas.'
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    parent = TreeForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='filhas', verbose_name='Conta-mãe'
    )

    class MPTTMeta:
        order_insertion_by = ['codigo']

    class Meta:
        verbose_name = 'Conta'
        verbose_name_plural = 'Plano de Contas'

    def __str__(self):
        return f'{self.codigo} — {self.nome}'

    def clean(self):
        # Regra 1 — só contas Analíticas recebem lançamentos de movimento.
        if self.tipo == 'S':
            self.permite_lancamento = False

        # Regra 2 — o código da filha tem de começar pelo código da mãe,
        # para a árvore ficar sempre coerente (ex.: mãe "1" -> filha "1.1").
        if self.parent_id:
            mae = PlanoContas.objects.filter(pk=self.parent_id).first()
            if mae and self.codigo and not self.codigo.startswith(mae.codigo):
                raise ValidationError({
                    'codigo': f'O código deve começar por "{mae.codigo}" '
                              f'(código da conta-mãe selecionada).'
                })

        # Regra 3 — uma conta que já tem subcontas não pode ser Analítica,
        # porque já deixou de ser uma conta de movimento direto.
        if self.pk and self.tipo == 'A' and self.filhas.exists():
            raise ValidationError({
                'tipo': 'Esta conta já tem subcontas — passe-a para o tipo '
                        'Sintética antes de gravar.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @staticmethod
    def sugerir_codigo(parent_id=None):
        """
        Sugere automaticamente o próximo código livre, para o utilizador
        não ter de pensar em numeração ao criar uma conta nova.
        """
        if parent_id:
            mae = PlanoContas.objects.filter(pk=parent_id).first()
            if not mae:
                return ''
            irmas = mae.filhas.order_by('-codigo')
            if irmas.exists():
                ultimo_codigo = irmas.first().codigo
                base, sep, sufixo = ultimo_codigo.rpartition('.')
                if sufixo.isdigit():
                    novo_sufixo = str(int(sufixo) + 1).zfill(len(sufixo))
                    return f'{base}{sep}{novo_sufixo}' if base else novo_sufixo
                return f'{ultimo_codigo}.1'
            # primeira filha desta mãe
            return f'{mae.codigo}.1' if '.' in mae.codigo else f'{mae.codigo}.1'
        else:
            ultima_raiz = PlanoContas.objects.filter(parent__isnull=True).order_by('-codigo').first()
            if ultima_raiz and ultima_raiz.codigo.isdigit():
                return str(int(ultima_raiz.codigo) + 1)
            return '1'

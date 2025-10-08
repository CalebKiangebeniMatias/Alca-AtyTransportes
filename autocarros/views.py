"""Views da app `autocarros` — organizadas com comentários descritivos e imports limpos.

Seções:
- imports (padrão, django, app)
- helpers e decorators
- autenticação / gestão de utilizadores
- CRUD de sectores, autocarros, despesas e relatórios
- views de listagem/agrupamento (registos / relatórios validados)
- dashboards e utilitários
"""

# ----- imports: biblioteca padrão -----
from datetime import date, datetime
from decimal import Decimal
from collections import defaultdict
import json
from urllib.parse import quote_plus

# ----- imports: Django -----
from django import forms
from django.db.models import Sum, F, DecimalField, Q, Count, ExpressionWrapper
from django.db.models.functions import TruncMonth
from django.forms import modelformset_factory
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views import View

# ----- imports: app local (models, forms, decorators) -----
from autocarros.decorators import acesso_restrito
from .models import (
    Autocarro, Comprovativo, ComprovativoRelatorio, DespesaCombustivel,
    RegistoDiario, Despesa, RelatorioSector, Sector, Motorista, CustomUser
)
from .forms import (
    DespesaCombustivelForm, EstadoAutocarroForm, AutocarroForm, DespesaForm,
    ComprovativoFormSet, MultiFileForm, RegistoDiarioFormSet, RegistoDiarioForm,
    RelatorioSectorForm, SectorForm, SectorGestorForm, SelecionarSectorCombustivelForm,
    CustomUserCreationForm, CustomAuthenticationForm, UserUpdateForm
)

# ----- Helpers / utilitários -----
def decimal_default(obj):
    """Serializador simples para objetos Decimal (usado no json.dumps)."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

# ----- Decorators personalizados -----
# Os wrappers abaixo garantem checagens adicionais (user_passes_test) quando necessário.
def admin_required(view_func):
    """Decorator: apenas utilizadores com método is_admin() ou nivel_acesso 'admin'."""
    decorated = user_passes_test(
        lambda user: user.is_authenticated and (hasattr(user, "is_admin") and user.is_admin() or getattr(user, "nivel_acesso", "").lower() == "admin"),
        login_url='acesso_negado'
    )(view_func)
    return decorated

def gestor_required(view_func):
    """Decorator: apenas gestores."""
    decorated = user_passes_test(
        lambda user: user.is_authenticated and (hasattr(user, "is_gestor") and user.is_gestor() or getattr(user, "nivel_acesso", "").lower() == "gestor"),
        login_url='acesso_negado'
    )(view_func)
    return decorated

def can_edit_required(view_func):
    """Decorator: apenas utilizadores com permissão de edição (can_edit())."""
    decorated = user_passes_test(
        lambda user: user.is_authenticated and (hasattr(user, "can_edit") and user.can_edit()),
        login_url='acesso_negado'
    )(view_func)
    return decorated

# ----- Autenticação e gestão de utilizadores -----
class LoginView(View):
    """Login simples (formulário custom)."""
    def get(self, request):
        return render(request, 'auth/login.html')

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f"Bem-vindo(a), {user.username}!")
            return redirect('dashboard')
        messages.error(request, "Usuário ou senha incorretos.")
        return render(request, 'auth/login.html')

@login_required
@acesso_restrito(['admin'])
def register_user(request):
    """Criar um novo utilizador — acessível apenas a administradores."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        telefone = request.POST.get('telefone')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm')
        nivel = request.POST.get('nivel_acesso')

        if password != confirm:
            messages.error(request, "As senhas não coincidem.")
            return redirect('register')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Nome de usuário já existe.")
            return redirect('register')

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            telefone=telefone,
            nivel_acesso=nivel
        )

        messages.success(request, f"Usuário '{user.username}' criado com sucesso!")
        return redirect('dashboard')

    niveis = CustomUser.NIVEL_ACESSO_CHOICES
    return render(request, 'auth/register.html', {'niveis': niveis})

@login_required
def logout_view(request):
    """Logout do utilizador."""
    logout(request)
    return redirect('login')

@login_required
@acesso_restrito(['admin'])
def admin_dashboard(request):
    """Painel de administração: listagem rápida de utilizadores."""
    usuarios = CustomUser.objects.all()
    context = {
        'usuarios': usuarios,
        'total_usuarios': usuarios.count(),
        'usuarios_ativos': usuarios.filter(ativo=True).count(),
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
def perfil(request):
    """Ver / editar perfil do utilizador actual (template separado)."""
    return render(request, 'autocarros/perfil.html', {'user': request.user})

@login_required
@acesso_restrito(['admin'])
def gerir_usuarios(request):
    """Listar utilizadores para gestão (admin)."""
    usuarios = CustomUser.objects.all().order_by('-date_joined')
    return render(request, 'gerir_usuarios.html', {'usuarios': usuarios})

@login_required
@acesso_restrito(['admin'])
def editar_usuario(request, user_id):
    """Editar dados de um utilizador existente."""
    usuario = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f'Usuário {usuario.username} atualizado com sucesso!')
            return redirect('gerir_usuarios')
    else:
        form = UserUpdateForm(instance=usuario)
    return render(request, 'editar_usuario.html', {'form': form, 'usuario': usuario})

def acesso_negado(request):
    """Página simples para acesso negado (HTTP 403)."""
    return render(request, 'acesso_negado.html', status=403)

# ----- Gestão de Sectores (CRUD) -----
@login_required
@acesso_restrito(['admin'])
def lista_sectores(request):
    """Listar todos os sectores (apenas admin)."""
    sectores = Sector.objects.all().order_by("nome")
    return render(request, "autocarros/lista_sectores.html", {"sectores": sectores})

@login_required
@acesso_restrito(['admin'])
def adicionar_sector(request):
    """Criar um novo sector."""
    if request.method == "POST":
        form = SectorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Setor adicionado com sucesso!")
            return redirect("lista_sectores")
        messages.error(request, "❌ Erro ao adicionar setor. Verifique os dados.")
    else:
        form = SectorForm()
    return render(request, "autocarros/adicionar_sector.html", {"form": form})

@login_required
@acesso_restrito(['admin'])
def editar_sector(request, pk):
    """Editar um sector existente."""
    sector = get_object_or_404(Sector, pk=pk)
    if request.method == "POST":
        form = SectorForm(request.POST, instance=sector)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Setor atualizado com sucesso!")
            return redirect("lista_sectores")
        messages.error(request, "❌ Erro ao atualizar setor. Verifique os dados.")
    else:
        form = SectorForm(instance=sector)
    return render(request, "autocarros/adicionar_sector.html", {"form": form, "editar": True})

@login_required
@acesso_restrito(['admin'])
def apagar_sector(request, pk):
    """Apagar um sector (com confirmação)."""
    sector = get_object_or_404(Sector, pk=pk)
    if request.method == "POST":
        try:
            sector.delete()
            messages.success(request, "✅ Setor apagado com sucesso!")
            return redirect("lista_sectores")
        except Exception as e:
            messages.error(request, f"❌ Erro ao apagar setor: {str(e)}")
    return render(request, "autocarros/confirmar_apagar_sector.html", {"sector": sector})

@login_required
@acesso_restrito(['admin'])
def associar_gestor(request, sector_id):
    """Associar um gestor a um sector (form)."""
    sector = get_object_or_404(Sector, id=sector_id)
    if request.method == "POST":
        form = SectorGestorForm(request.POST, instance=sector)
        if form.is_valid():
            form.save()
            messages.success(request, f'Gestor associado ao setor "{sector.nome}" com sucesso!')
            return redirect('lista_sectores')
    else:
        form = SectorGestorForm(instance=sector)
    return render(request, "autocarros/associar_gestor.html", {"form": form, "sector": sector})

# ----- Verificações / manutenção de integridade -----
@login_required
@acesso_restrito(['admin'])
def verificar_integridade(request):
    """Verifica e corrige problemas comuns (registos sem relatório, relatórios vazios, duplicatas)."""
    if not request.user.is_superuser:
        messages.error(request, "❌ Apenas administradores podem acessar esta função.")
        return redirect('listar_registros')

    problemas = []

    # Registros sem relatório associado
    registros_sem_relatorio = RegistoDiario.objects.filter(relatorio__isnull=True)
    if registros_sem_relatorio.exists():
        problemas.append(f"❌ {registros_sem_relatorio.count()} registros sem relatório associado")

    # Relatórios sem registros
    relatorios_sem_registros = RelatorioSector.objects.filter(registos__isnull=True)
    if relatorios_sem_registros.exists():
        problemas.append(f"❌ {relatorios_sem_registros.count()} relatórios sem registros")

    # Duplicações (por relatorio + autocarro)
    duplicatas = RegistoDiario.objects.values('relatorio', 'autocarro').annotate(count=Count('id')).filter(count__gt=1)
    if duplicatas.exists():
        problemas.append(f"❌ {duplicatas.count()} duplicatas encontradas")

    # Correções rápidas se solicitadas via POST
    if request.method == "POST" and "corrigir" in request.POST:
        for registro in registros_sem_relatorio:
            relatorio_compativel = RelatorioSector.objects.filter(sector=registro.autocarro.sector, data=registro.data).first()
            if relatorio_compativel:
                registro.relatorio = relatorio_compativel
                registro.save()
        for relatorio in relatorios_sem_registros:
            autocarros = Autocarro.objects.filter(sector=relatorio.sector)
            for autocarro in autocarros:
                RegistoDiario.objects.get_or_create(relatorio=relatorio, autocarro=autocarro, defaults={'data': relatorio.data})
        messages.success(request, "✅ Problemas de integridade corrigidos!")
        return redirect('verificar_integridade')

    context = {'problemas': problemas, 'total_problemas': len(problemas)}
    return render(request, "autocarros/verificar_integridade.html", context)

# ----- Dashboard / Listagens principais -----
@login_required
@acesso_restrito(['admin'])
def dashboard(request):
    """Painel principal com agregações por mês e por autocarro."""
    hoje = timezone.now().date()
    mes_param = request.GET.get("mes", hoje.strftime("%Y-%m"))
    try:
        ano, mes = map(int, mes_param.split("-"))
    except Exception:
        ano, mes = hoje.year, hoje.month

    anos_disponiveis = [int(d.year) for d in RegistoDiario.objects.dates("data", "year", order="DESC")]
    if hoje.year not in anos_disponiveis:
        anos_disponiveis.insert(0, hoje.year)

    registos = RegistoDiario.objects.filter(data__year=ano, data__month=mes).select_related("autocarro")

    # Agregar despesas de combustível para os registos do mês (por autocarro/data)
    combustivel_map_dashboard = {}
    if registos.exists():
        autocarro_ids = set(registos.values_list('autocarro_id', flat=True))
        datas = set(registos.values_list('data', flat=True))
        combustiveis_dash = DespesaCombustivel.objects.filter(autocarro_id__in=autocarro_ids, data__in=datas)
        agg_dash = defaultdict(lambda: {'total_valor': Decimal('0'), 'total_valor_litros': Decimal('0'), 'total_sobragem': Decimal('0'), 'total_lavagem': Decimal('0')})
        for c in combustiveis_dash:
            key = f"{c.autocarro_id}_{c.data.isoformat()}"
            agg_dash[key]['total_valor'] += c.valor or Decimal('0')
            agg_dash[key]['total_valor_litros'] += c.valor_litros or Decimal('0')
            agg_dash[key]['total_sobragem'] += c.sobragem_filtros or Decimal('0')
            agg_dash[key]['total_lavagem'] += c.lavagem or Decimal('0')
        for k, v in agg_dash.items():
            combustivel_map_dashboard[k] = v

    # Totais gerais (entradas / saídas / combustível)
    total_entradas = registos.aggregate(total=Sum(F("normal") + F("alunos") + F("luvu") + F("frete"), output_field=DecimalField()))["total"] or Decimal("0")
    total_saidas_registos = registos.aggregate(total=Sum(F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"), output_field=DecimalField()))["total"] or Decimal("0")
    total_saidas_despesas = Despesa.objects.filter(data__year=ano, data__month=mes).aggregate(total=Sum("valor", output_field=DecimalField()))["total"] or Decimal("0")
    total_combustivel = DespesaCombustivel.objects.filter(data__year=ano, data__month=mes).aggregate(
        total_valor=Sum('valor', output_field=DecimalField()),
        total_litros=Sum('valor_litros', output_field=DecimalField()),
        total_sobragem=Sum('sobragem_filtros', output_field=DecimalField()),
        total_lavagem=Sum('lavagem', output_field=DecimalField()),
    )
    total_combustivel_valor = total_combustivel.get('total_valor') or Decimal('0')
    total_combustivel_litros = total_combustivel.get('total_litros') or Decimal('0')
    total_combustivel_sobragem = total_combustivel.get('total_sobragem') or Decimal('0')
    total_combustivel_lavagem = total_combustivel.get('total_lavagem') or Decimal('0')

    total_saidas = total_saidas_registos + total_saidas_despesas + total_combustivel_valor + total_combustivel_sobragem + total_combustivel_lavagem
    total_resto = total_entradas - total_saidas

    # Estatísticas por autocarro (incluir combustível nas saídas)
    autocarros_stats = []
    for autocarro in Autocarro.objects.all():
        registos_auto = registos.filter(autocarro=autocarro)
        stats = {
            "autocarro": autocarro,
            "total_km": registos_auto.aggregate(Sum("km_percorridos"))["km_percorridos__sum"] or 0,
            "total_entradas": registos_auto.aggregate(total=Sum(F("normal") + F("alunos") + F("luvu") + F("frete"), output_field=DecimalField()))["total"] or 0,
            "total_saidas": registos_auto.aggregate(total=Sum(F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"), output_field=DecimalField()))["total"] or 0,
            "total_passageiros": registos_auto.aggregate(Sum("numero_passageiros"))["numero_passageiros__sum"] or 0,
            "total_viagens": registos_auto.aggregate(Sum("numero_viagens"))["numero_viagens__sum"] or 0,
        }
        comb_auto = DespesaCombustivel.objects.filter(autocarro=autocarro, data__year=ano, data__month=mes).aggregate(
            total_valor=Sum('valor', output_field=DecimalField()),
            total_litros=Sum('valor_litros', output_field=DecimalField()),
            total_sobragem=Sum('sobragem_filtros', output_field=DecimalField()),
            total_lavagem=Sum('lavagem', output_field=DecimalField()),
        )
        stats['total_combustivel'] = comb_auto.get('total_valor') or Decimal('0')
        stats['total_combustivel_litros'] = comb_auto.get('total_litros') or Decimal('0')
        stats['total_combustivel_sobragem'] = comb_auto.get('total_sobragem') or Decimal('0')
        stats['total_combustivel_lavagem'] = comb_auto.get('total_lavagem') or Decimal('0')

        try:
            orig_saidas = Decimal(stats.get('total_saidas') or 0)
        except Exception:
            orig_saidas = Decimal('0')
        stats['total_saidas'] = orig_saidas + stats.get('total_combustivel', Decimal('0')) + stats.get('total_combustivel_sobragem', Decimal('0')) + stats.get('total_combustivel_lavagem', Decimal('0'))
        stats["resto"] = stats["total_entradas"] - stats['total_saidas']
        autocarros_stats.append(stats)

    # Preparar registos recentes com dados de combustível anexados
    registos_recentes_qs = registos.order_by("-data")[:10]
    registos_recentes = []
    for reg in registos_recentes_qs:
        key = f"{reg.autocarro_id}_{reg.data.isoformat()}"
        comb = combustivel_map_dashboard.get(key, {})
        reg.combustivel_total = comb.get('total_valor', Decimal('0'))
        reg.combustivel_valor_litros = comb.get('total_valor_litros', Decimal('0'))
        reg.combustivel_sobragem = comb.get('total_sobragem', Decimal('0'))
        reg.combustivel_lavagem = comb.get('total_lavagem', Decimal('0'))
        try:
            reg.saidas_total_incl_combustivel = reg.saidas_total() + reg.combustivel_total + reg.combustivel_sobragem + reg.combustivel_lavagem
        except Exception:
            reg.saidas_total_incl_combustivel = reg.saidas_total()
        try:
            reg.saldo_liquido_incl_combustivel = reg.entradas_total() - reg.saidas_total_incl_combustivel
        except Exception:
            reg.saldo_liquido_incl_combustivel = reg.saldo_liquido()
        registos_recentes.append(reg)

    context = {
        "ano": ano,
        "mes": f"{ano}-{mes:02d}",
        "anos_disponiveis": anos_disponiveis,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "total_resto": total_resto,
        "total_combustivel_valor": total_combustivel_valor,
        "total_combustivel_litros": total_combustivel_litros,
        "total_combustivel_sobragem": total_combustivel_sobragem,
        "total_combustivel_lavagem": total_combustivel_lavagem,
        "autocarros_stats": autocarros_stats,
        "registos_recentes": registos_recentes,
    }
    return render(request, "autocarros/dashboard.html", context)

# ----- Resumo por sector (acesso controlado) -----
@login_required
@acesso_restrito(['admin', 'gestor'])
def resumo_sector(request, slug):
    """Resumo financeiro e operacional de um sector (filtra por datas opcionais)."""
    sector_obj = get_object_or_404(Sector, slug=slug)
    nivel = getattr(request.user, "nivel_acesso", "").lower()

    # Validações de acesso baseadas no nível do utilizador
    if nivel == 'gestor':
        if sector_obj.gestor_id != request.user.id:
            return redirect('acesso_negado')
    elif nivel == 'associado':
        if not sector_obj.associados.filter(pk=request.user.pk).exists():
            return redirect('acesso_negado')
    elif nivel in ['admin']:
        pass
    else:
        return redirect('acesso_negado')

    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    registos = RegistoDiario.objects.filter(autocarro__sector=sector_obj).select_related("autocarro")
    if data_inicio:
        registos = registos.filter(data__gte=parse_date(data_inicio))
    if data_fim:
        registos = registos.filter(data__lte=parse_date(data_fim))

    # Totais e agregações (entradas/saídas/combustível/despesas)
    total_entradas = registos.aggregate(total=Sum(F("normal") + F("alunos") + F("luvu") + F("frete"), output_field=DecimalField()))["total"] or 0
    total_saidas = registos.aggregate(total=Sum(F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"), output_field=DecimalField()))["total"] or 0
    total_km = registos.aggregate(Sum("km_percorridos"))["km_percorridos__sum"] or 0
    total_passageiros = registos.aggregate(Sum("numero_passageiros"))["numero_passageiros__sum"] or 0
    total_viagens = registos.aggregate(Sum("numero_viagens"))["numero_viagens__sum"] or 0

    combustivel_agregado = DespesaCombustivel.objects.filter(autocarro__sector=sector_obj)
    if data_inicio:
        combustivel_agregado = combustivel_agregado.filter(data__gte=parse_date(data_inicio))
    if data_fim:
        combustivel_agregado = combustivel_agregado.filter(data__lte=parse_date(data_fim))

    comb_totais = combustivel_agregado.aggregate(
        total_valor=Sum('valor', output_field=DecimalField()),
        total_litros=Sum('valor_litros', output_field=DecimalField()),
        total_sobragem=Sum('sobragem_filtros', output_field=DecimalField()),
        total_lavagem=Sum('lavagem', output_field=DecimalField()),
    )
    total_combustivel_valor = comb_totais.get('total_valor') or Decimal('0')
    total_combustivel_litros = comb_totais.get('total_litros') or Decimal('0')
    total_combustivel_sobragem = comb_totais.get('total_sobragem') or Decimal('0')
    total_combustivel_lavagem = comb_totais.get('total_lavagem') or Decimal('0')

    total_saidas_incl_combustivel = total_saidas + total_combustivel_valor + total_combustivel_sobragem + total_combustivel_lavagem

    despesas_qs = Despesa.objects.filter(sector=sector_obj)
    if data_inicio:
        despesas_qs = despesas_qs.filter(data__gte=parse_date(data_inicio))
    if data_fim:
        despesas_qs = despesas_qs.filter(data__lte=parse_date(data_fim))
    despesas_totais_ag = despesas_qs.aggregate(total=Sum('valor', output_field=DecimalField()))
    total_despesas_sector = despesas_totais_ag.get('total') or Decimal('0')

    total_saidas_final = total_saidas_incl_combustivel + total_despesas_sector
    resto = total_entradas - total_saidas_final

    # Estatísticas por autocarro no sector
    autocarros_stats = []
    for autocarro in Autocarro.objects.filter(sector=sector_obj):
        registos_auto = registos.filter(autocarro=autocarro)
        stats = {
            "autocarro": autocarro,
            "total_entradas": registos_auto.aggregate(total=Sum(F("normal") + F("alunos") + F("luvu") + F("frete"), output_field=DecimalField()))["total"] or 0,
            "total_saidas": registos_auto.aggregate(total=Sum(F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"), output_field=DecimalField()))["total"] or 0,
            "total_km": registos_auto.aggregate(Sum("km_percorridos"))["km_percorridos__sum"] or 0,
            "total_passageiros": registos_auto.aggregate(Sum("numero_passageiros"))["numero_passageiros__sum"] or 0,
            "total_viagens": registos_auto.aggregate(Sum("numero_viagens"))["numero_viagens__sum"] or 0,
        }
        comb_auto = combustivel_agregado.filter(autocarro=autocarro).aggregate(
            total_valor=Sum('valor', output_field=DecimalField()),
            total_litros=Sum('valor_litros', output_field=DecimalField()),
            total_sobragem=Sum('sobragem_filtros', output_field=DecimalField()),
            total_lavagem=Sum('lavagem', output_field=DecimalField()),
        )
        stats['total_combustivel'] = comb_auto.get('total_valor') or Decimal('0')
        stats['total_combustivel_litros'] = comb_auto.get('total_litros') or Decimal('0')
        stats['total_combustivel_sobragem'] = comb_auto.get('total_sobragem') or Decimal('0')
        stats['total_combustivel_lavagem'] = comb_auto.get('total_lavagem') or Decimal('0')
        stats['total_saidas'] = stats['total_saidas'] + stats.get('total_combustivel', Decimal('0')) + stats.get('total_combustivel_sobragem', Decimal('0')) + stats.get('total_combustivel_lavagem', Decimal('0'))
        stats["resto"] = stats["total_entradas"] - stats["total_saidas"]
        autocarros_stats.append(stats)

    # Mensagem / link para WhatsApp — texto formatado
    try:
        lines = []
        periodo = f"{data_inicio or '—'} até {data_fim or '—'}"
        lines.append(f"Resumo do Sector: {sector_obj.nome}")
        lines.append(f"Período: {periodo}")
        lines.append("")
        lines.append("Totais:")
        lines.append(f"- Entradas: {float(total_entradas):,.2f} Kz")
        lines.append(f"- Saídas (incl. comb.): {float(total_saidas_incl_combustivel):,.2f} Kz")
        lines.append(f"- Combustível: {float(total_combustivel_valor):,.2f} Kz | Litros: {float(total_combustivel_litros):,.2f}")
        lines.append(f"- Resto: {float(resto):,.2f} Kz")
        lines.append("")
        lines.append("Resumo por Autocarro:")
        for s in autocarros_stats:
            try:
                ent = float(s.get('total_entradas', 0) or 0)
                sai = float(s.get('total_saidas', 0) or 0)
                res = float(s.get('resto', 0) or 0)
                lines.append(f"- {s['autocarro'].numero}: Entradas {ent:,.2f} Kz | Saídas {sai:,.2f} Kz | Resto {res:,.2f} Kz")
            except Exception:
                continue

        lines.append("")
        lines.append("Despesas do Sector (últimas):")
        despesas = Despesa.objects.filter(sector=sector_obj).order_by('-data')[:10]
        if despesas:
            for d in despesas:
                try:
                    lines.append(f"- {d.data}: {d.descricao} — {float(d.valor):,.2f} Kz ({d.comprovativos.count()} comprov.)")
                except Exception:
                    lines.append(f"- {d.data}: {d.descricao} — {d.valor} Kz")
        else:
            lines.append("- Nenhuma despesa registrada no período.")

        lines.append("")
        lines.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        whatsapp_text = "\n".join(lines)
        whatsapp_link = "https://api.whatsapp.com/send?text=" + quote_plus(whatsapp_text)
    except Exception:
        whatsapp_text = "Resumo do sector não disponível"
        whatsapp_link = "https://api.whatsapp.com/send?text=" + quote_plus(whatsapp_text)

    context = {
        "sector": sector_obj,
        "autocarros_stats": autocarros_stats,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas_final,
        "total_km": total_km,
        "total_passageiros": total_passageiros,
        "total_viagens": total_viagens,
        "resto": resto,
        "total_combustivel_valor": total_combustivel_valor,
        "total_combustivel_litros": total_combustivel_litros,
        "total_combustivel_sobragem": total_combustivel_sobragem,
        "total_combustivel_lavagem": total_combustivel_lavagem,
        "total_despesas_sector": total_despesas_sector,
        "chart_entradas": float(total_entradas),
        "chart_saidas": float(total_saidas_final),
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "despesas_sector": despesas,
        "whatsapp_message": whatsapp_text,
        "whatsapp_link": whatsapp_link,
    }
    return render(request, "autocarros/resumo_sector.html", context)

# ----- Detalhe / CRUD de Autocarros -----
@login_required
@acesso_restrito(['admin'])
def detalhe_autocarro(request, autocarro_id):
    """Resumo detalhado e últimos registos de um autocarro específico."""
    autocarro = get_object_or_404(Autocarro, id=autocarro_id)
    registos_local = RegistoDiario.objects.filter(autocarro=autocarro)

    entradas = registos_local.aggregate(total=Sum(F("normal") + F("alunos") + F("luvu") + F("frete"), output_field=DecimalField()))["total"] or 0
    saidas = registos_local.aggregate(total=Sum(F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"), output_field=DecimalField()))["total"] or 0
    km = registos_local.aggregate(Sum('km_percorridos'))['km_percorridos__sum'] or 0
    passageiros = registos_local.aggregate(Sum('numero_passageiros'))['numero_passageiros__sum'] or 0
    viagens = registos_local.aggregate(Sum('numero_viagens'))['numero_viagens__sum'] or 0

    combustiveis_qs = DespesaCombustivel.objects.filter(autocarro=autocarro, data__in=registos_local.values_list('data', flat=True))
    comb_map = defaultdict(lambda: {'total_valor': Decimal('0'), 'total_valor_litros': Decimal('0'), 'total_sobragem': Decimal('0'), 'total_lavagem': Decimal('0')})
    total_combustivel_valor = total_combustivel_litros = total_combustivel_sobragem = total_combustivel_lavagem = Decimal('0')

    for c in combustiveis_qs:
        key = c.data.isoformat()
        comb_map[key]['total_valor'] += c.valor or Decimal('0')
        comb_map[key]['total_valor_litros'] += c.valor_litros or Decimal('0')
        comb_map[key]['total_sobragem'] += c.sobragem_filtros or Decimal('0')
        comb_map[key]['total_lavagem'] += c.lavagem or Decimal('0')
        total_combustivel_valor += c.valor or Decimal('0')
        total_combustivel_litros += c.valor_litros or Decimal('0')
        total_combustivel_sobragem += c.sobragem_filtros or Decimal('0')
        total_combustivel_lavagem += c.lavagem or Decimal('0')

    for r in registos_local:
        key = r.data.isoformat()
        agg = comb_map.get(key, {})
        r.combustivel_total = agg.get('total_valor', Decimal('0'))
        r.combustivel_valor_litros = agg.get('total_valor_litros', Decimal('0'))
        r.combustivel_sobragem = agg.get('total_sobragem', Decimal('0'))
        r.combustivel_lavagem = agg.get('total_lavagem', Decimal('0'))
        try:
            r.saidas_total_incl_combustivel = r.saidas_total() + r.combustivel_total
        except Exception:
            r.saidas_total_incl_combustivel = r.saidas_total()
        try:
            r.saldo_liquido_incl_combustivel = r.entradas_total() - r.saidas_total_incl_combustivel
        except Exception:
            r.saldo_liquido_incl_combustivel = r.saldo_liquido()
        try:
            if r.combustivel_valor_litros and r.combustivel_valor_litros != Decimal('0'):
                r.preco_litro = r.combustivel_total / r.combustivel_valor_litros
            else:
                r.preco_litro = None
        except Exception:
            r.preco_litro = None

    resto = entradas - (saidas + total_combustivel_valor)
    total_saidas_incl_combustivel = saidas + total_combustivel_valor + total_combustivel_sobragem + total_combustivel_lavagem

    contexto = {
        'autocarro': autocarro,
        'total_entradas': entradas,
        'total_saidas': total_saidas_incl_combustivel,
        'total_km': km,
        'total_passageiros': passageiros,
        'total_viagens': viagens,
        'resto': resto,
        'total_combustivel_valor': total_combustivel_valor,
        'total_combustivel_litros': total_combustivel_litros,
        'total_combustivel_sobragem': total_combustivel_sobragem,
        'total_combustivel_lavagem': total_combustivel_lavagem,
        'registos': registos_local.order_by('-data')[:10],
    }
    return render(request, 'autocarros/detalhe_autocarro.html', contexto)

# ----- Listagem e edição de registos diários (agrupados por sector/data) -----
@login_required
@acesso_restrito(['admin', 'gestor'])
def listar_registros(request):
    """Listagem principal de registos — suporta filtros por sector/data e agrupa para exibição."""
    hoje = timezone.now().date()
    sector_id = request.GET.get('sector', '').strip()
    data_inicio = request.GET.get('data_inicio', hoje.isoformat())
    data_fim = request.GET.get('data_fim', hoje.isoformat())
    nivel = getattr(request.user, "nivel_acesso", "").lower()

    sector_obj = None
    if sector_id:
        sector_obj = get_object_or_404(Sector, id=sector_id)

    # Determinar setores permitidos conforme nível de acesso
    if nivel == 'gestor':
        if sector_obj:
            if sector_obj.gestor_id != request.user.id:
                return redirect('acesso_negado')
        else:
            sectores_permitidos = Sector.objects.filter(gestor=request.user)
    elif nivel == 'associado':
        if sector_obj:
            if not sector_obj.associados.filter(pk=request.user.pk).exists():
                return redirect('acesso_negado')
        else:
            sectores_permitidos = Sector.objects.filter(associados=request.user)
    elif nivel in ['admin', 'superuser']:
        sectores_permitidos = Sector.objects.all()
    else:
        return redirect('acesso_negado')

    registros = RegistoDiario.objects.select_related('autocarro__sector')
    if sector_obj:
        registros = registros.filter(autocarro__sector=sector_obj)
    else:
        registros = registros.filter(autocarro__sector__in=sectores_permitidos)

    if data_inicio:
        registros = registros.filter(data__gte=data_inicio)
    if data_fim:
        registros = registros.filter(data__lte=data_fim)

    # Agregar despesas de combustível por autocarro/data para anexar aos registos
    combustivel_map = {}
    if registros.exists():
        autocarro_ids = set(registros.values_list('autocarro_id', flat=True))
        datas = set(registros.values_list('data', flat=True))
        combustiveis = DespesaCombustivel.objects.filter(autocarro_id__in=autocarro_ids, data__in=datas)
        agg = defaultdict(lambda: {
            'total_valor': Decimal('0'),
            'total_valor_litros': Decimal('0'),
            'total_sobragem_filtros': Decimal('0'),
            'total_lavagem': Decimal('0'),
            'comprovativos': []
        })
        for c in combustiveis:
            key = f"{c.autocarro_id}_{c.data.isoformat()}"
            agg[key]['total_valor'] += c.valor or Decimal('0')
            agg[key]['total_valor_litros'] += c.valor_litros or Decimal('0')
            agg[key]['total_sobragem_filtros'] += c.sobragem_filtros or Decimal('0')
            agg[key]['total_lavagem'] += c.lavagem or Decimal('0')
            if c.comprovativo:
                agg[key]['comprovativos'].append(getattr(c.comprovativo, 'url', str(c.comprovativo)))
        for k, v in agg.items():
            combustivel_map[k] = v

    registros = registros.order_by('-data', 'autocarro__sector__nome', 'autocarro__numero')

    # Agrupar por data+sector para exibição (mesma estrutura usada nos templates)
    registros_agrupados = {}
    for registro in registros:
        chave = f"{registro.data.isoformat()}_{registro.autocarro.sector.id}"
        if chave not in registros_agrupados:
            registros_agrupados[chave] = {
                'data': registro.data,
                'sector': registro.autocarro.sector,
                'registos': [],
                'total_entradas': Decimal('0'),
                'total_saidas': Decimal('0'),
                'total_saldo': Decimal('0'),
            }
        key = f"{registro.autocarro_id}_{registro.data.isoformat()}"
        comb = combustivel_map.get(key)
        if comb:
            registro.combustivel_total = comb.get('total_valor', Decimal('0'))
            registro.combustivel_valor_litros = comb.get('total_valor_litros', Decimal('0'))
            registro.combustivel_sobragem = comb.get('total_sobragem_filtros', Decimal('0'))
            registro.combustivel_lavagem = comb.get('total_lavagem', Decimal('0'))
            registro.comprovativos_combustivel = comb.get('comprovativos', [])
        else:
            registro.combustivel_total = registro.combustivel_valor_litros = registro.combustivel_sobragem = registro.combustivel_lavagem = Decimal('0')
            registro.comprovativos_combustivel = []

        try:
            registro.saidas_total_incl_combustivel = registro.saidas_total() + registro.combustivel_total + registro.combustivel_sobragem + registro.combustivel_lavagem
        except Exception:
            registro.saidas_total_incl_combustivel = registro.saidas_total()
        try:
            registro.saldo_liquido_incl_combustivel = registro.entradas_total() - registro.saidas_total_incl_combustivel
        except Exception:
            registro.saldo_liquido_incl_combustivel = registro.saldo_liquido()
        try:
            registro.preco_litro = (registro.combustivel_total / registro.combustivel_valor_litros) if registro.combustivel_valor_litros else None
        except Exception:
            registro.preco_litro = None

        registros_agrupados[chave]['registos'].append(registro)
        registros_agrupados[chave]['total_entradas'] += registro.entradas_total()
        registros_agrupados[chave]['total_saidas'] += registro.saidas_total_incl_combustivel
        registros_agrupados[chave]['total_saldo'] += registro.entradas_total() - registro.saidas_total_incl_combustivel

    # Totais gerais calculados a partir da lista `registros`
    total_entradas = total_saidas = total_saldo = total_combustivel = Decimal('0')
    for reg in registros:
        try:
            total_entradas += reg.entradas_total()
        except Exception:
            total_entradas += Decimal('0')
        try:
            total_saidas += getattr(reg, 'saidas_total_incl_combustivel', reg.saidas_total())
        except Exception:
            total_saidas += Decimal('0')
        try:
            total_saldo += getattr(reg, 'saldo_liquido_incl_combustivel', reg.saldo_liquido())
        except Exception:
            total_saldo += Decimal('0')
        try:
            total_combustivel += getattr(reg, 'combustivel_total', Decimal('0'))
        except Exception:
            total_combustivel += Decimal('0')

    totais = {
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'total_saldo': total_saldo,
        'total_autocarros': registros.count(),
        'total_combustivel': total_combustivel,
    }

    # Preparar link WhatsApp para cada grupo
    for g in registros_agrupados.values():
        try:
            data_str = g['data'].strftime('%d/%m/%Y')
        except Exception:
            data_str = str(g['data'])
        sector_name = g['sector'].nome if g.get('sector') else 'Geral'
        descricao = '-'
        if g['registos'] and getattr(g['registos'][0], 'relatorio', None):
            descricao = g['registos'][0].relatorio.descricao or '-'

        parts = [f"📅 DATA: {data_str}", f"🏢 RELATÓRIO DO DIA: {sector_name}", "", f"📝 DESCRIÇÃO: {descricao}"]
        for reg in g['registos']:
            parts += ["", "__________________________________________", "", f"🚌 Autocarro: {reg.autocarro.numero} - {reg.autocarro.modelo}",
                      f"👨‍✈️ Motorista: {reg.motorista or 'N/A'}", f"👨‍💼 Cobrador Principal: {reg.cobrador_principal or 'N/A'}"]
            if sector_name.lower() == 'luanda':
                parts += ["✅ Entradas (Manhã/Tarde)", f"Manhã (Normal): {reg.normal}", f"Tarde (Alunos): {reg.alunos}"]
            else:
                parts += ["✅ Entradas", f"Normal: {reg.normal}", f"Alunos: {reg.alunos}"]
            parts += [f"Luvu: {reg.luvu}", f"Frete: {reg.frete}", f"➡️ Total Entradas: {reg.entradas_total()}",
                      "", "❌ Saídas", f"Alimentação: {reg.alimentacao}", f"Parqueamento: {reg.parqueamento}",
                      f"Taxa: {reg.taxa}", f"Outros: {reg.outros}", f"Combustível (valor): {getattr(reg, 'combustivel_total', 0)}",
                      f"Sobragem/Filtros: {getattr(reg, 'combustivel_sobragem', 0)}", f"Lavagem: {getattr(reg, 'combustivel_lavagem', 0)}",
                      f"➡️ Total Saídas: {getattr(reg, 'saidas_total_incl_combustivel', reg.saidas_total())}",
                      "", "📊 Outros Dados", f"Kms: {reg.km_percorridos}", f"Passageiros: {reg.numero_passageiros}",
                      f"Viagens: {reg.numero_viagens}", "", f"💰 Saldo Liquído: {getattr(reg, 'saldo_liquido_incl_combustivel', reg.saldo_liquido())}"]
        parts += ["", "__________________________________________", "", "📊 Resumo", "", f"✅ Entrada Geral: {total_entradas}", "", f"❌ Saida Geral: {total_saidas}", "", f"💰 Liquído Geral: {total_saldo}"]
        message = '\n'.join(parts)
        g['whatsapp_link'] = f"https://wa.me/?text={quote_plus(message)}"

    sectores = Sector.objects.all()
    context = {
        'registros_agrupados': list(registros_agrupados.values()),
        'sectores': sectores,
        'sector_id': sector_id,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'totais': totais,
        'hoje': hoje,
        'combustivel_map': combustivel_map,
    }
    return render(request, 'autocarros/listar_registros.html', context)

# ----- Operações individuais (deletar, concluir, validar) -----
@login_required
def deletar_registros_sector_data(request, sector_id, data):
    sector = get_object_or_404(Sector, pk=sector_id)
    data_obj = parse_date(data)
    if not data_obj:
        messages.error(request, '❌ Data inválida.')
        return redirect('listar_registros')
    if request.method == 'POST':
        try:
            RegistoDiario.objects.filter(autocarro__sector=sector, data=data_obj).delete()
            RelatorioSector.objects.filter(sector=sector, data=data_obj).delete()
            messages.success(request, f'✅ Todos os registros e o relatório do setor {sector.nome} em {data_obj.strftime("%d/%m/%Y")} foram eliminados!')
            return redirect('listar_registros')
        except Exception as e:
            messages.error(request, f'❌ Erro ao eliminar registros: {str(e)}')
    return render(request, 'autocarros/confirmar_deletar_registros_sector.html', {'sector': sector, 'data': data_obj})

@login_required
def deletar_registro(request, pk):
    registro = get_object_or_404(RegistoDiario, pk=pk)
    if request.method == 'POST':
        try:
            registro.delete()
            messages.success(request, '✅ Registro eliminado com sucesso!')
            return redirect('listar_registros')
        except Exception as e:
            messages.error(request, f'❌ Erro ao eliminar registro: {str(e)}')
    return render(request, 'autocarros/confirmar_deletar_registro.html', {'registro': registro})

@login_required
def concluir_relatorio(request, pk):
    """Marca o relatório como concluído (log/feedback apenas)."""
    relatorio = get_object_or_404(RelatorioSector, pk=pk)
    if request.method == 'POST':
        try:
            messages.success(request, f"✅ Relatório de {relatorio.sector.nome} concluído com sucesso!")
        except Exception as e:
            messages.error(request, f"❌ Erro ao concluir relatório: {str(e)}")
    return redirect('listar_registros')

@login_required
@acesso_restrito(['admin'])
def validar_relatorio(request, pk):
    """Marca o relatório como validado — apenas admin (checagem redundante aplicada)."""
    relatorio = get_object_or_404(RelatorioSector, pk=pk)
    nivel = getattr(request.user, "nivel_acesso", "") or ""
    if not (hasattr(request.user, "is_admin") and request.user.is_admin()) and nivel.lower() != "admin":
        messages.error(request, "❌ Acesso negado. Apenas administradores podem validar relatórios.")
        return redirect('acesso_negado')
    if request.method == 'POST':
        try:
            if hasattr(relatorio, "validado"):
                relatorio.validado = True
                relatorio.save()
            messages.success(request, f"✅ Relatório de {relatorio.sector.nome} validado com sucesso!")
        except Exception as e:
            messages.error(request, f"❌ Erro ao validar relatório: {str(e)}")
    return redirect('listar_registros')

# ----- Relatórios validados (view de leitura) -----
@login_required
def relatorios_validados(request):
    """Listagem de registos já validados — filtros por sector/data aplicáveis."""
    sector_id = request.GET.get('sector', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    data_hoje = timezone.now().date()

    registos_validados = RegistoDiario.objects.filter(validado=True)
    if sector_id:
        registos_validados = registos_validados.filter(autocarro__sector_id=sector_id)
    if data_inicio:
        registos_validados = registos_validados.filter(data__gte=data_inicio)
    if data_fim:
        registos_validados = registos_validados.filter(data__lte=data_fim)
    if not data_inicio and not data_fim:
        registos_validados = registos_validados.filter(data=data_hoje)
        data_inicio = data_fim = data_hoje.isoformat()

    combustivel_map_validados = {}
    if registos_validados.exists():
        autocarro_ids = set(registos_validados.values_list('autocarro_id', flat=True))
        datas = set(registos_validados.values_list('data', flat=True))
        combustiveis_val = DespesaCombustivel.objects.filter(autocarro_id__in=autocarro_ids, data__in=datas)
        agg_val = defaultdict(lambda: {'total_valor': Decimal('0'), 'total_valor_litros': Decimal('0'), 'total_sobragem': Decimal('0'), 'total_lavagem': Decimal('0')})
        for c in combustiveis_val:
            key = f"{c.autocarro_id}_{c.data.isoformat()}"
            agg_val[key]['total_valor'] += c.valor or Decimal('0')
            agg_val[key]['total_valor_litros'] += c.valor_litros or Decimal('0')
            agg_val[key]['total_sobragem'] += c.sobragem_filtros or Decimal('0')
            agg_val[key]['total_lavagem'] += c.lavagem or Decimal('0')
        for k, v in agg_val.items():
            combustivel_map_validados[k] = v

    registos_por_data_sector = {}
    processed_registos = []
    for registro in registos_validados.select_related('autocarro__sector'):
        key = f"{registro.autocarro_id}_{registro.data.isoformat()}"
        comb = combustivel_map_validados.get(key, {})
        registro.combustivel_total = comb.get('total_valor', Decimal('0'))
        registro.combustivel_valor_litros = comb.get('total_valor_litros', Decimal('0'))
        registro.combustivel_sobragem = comb.get('total_sobragem', Decimal('0'))
        registro.combustivel_lavagem = comb.get('total_lavagem', Decimal('0'))
        try:
            registro.saidas_total_incl_combustivel = registro.saidas_total() + registro.combustivel_total + registro.combustivel_sobragem + registro.combustivel_lavagem
        except Exception:
            registro.saidas_total_incl_combustivel = registro.saidas_total()
        try:
            registro.saldo_liquido_incl_combustivel = registro.entradas_total() - registro.saidas_total_incl_combustivel
        except Exception:
            registro.saldo_liquido_incl_combustivel = registro.saldo_liquido()

        chave = f"{registro.data}_{registro.autocarro.sector.id}"
        if chave not in registos_por_data_sector:
            registos_por_data_sector[chave] = {
                'data': registro.data,
                'sector': registro.autocarro.sector,
                'registos': [],
                'total_entradas': Decimal('0'),
                'total_saidas': Decimal('0'),
                'total_saldo': Decimal('0'),
                'total_combustivel': Decimal('0'),
            }

        entradas_reg = Decimal(getattr(registro, 'entradas_total')() if callable(getattr(registro, 'entradas_total', None)) else 0)
        saidas_reg = Decimal(getattr(registro, 'saidas_total_incl_combustivel', registro.saidas_total()))
        saldo_reg = Decimal(getattr(registro, 'saldo_liquido_incl_combustivel', registro.saldo_liquido()))
        combustivel_reg = Decimal(getattr(registro, 'combustivel_total', Decimal('0')))

        registos_por_data_sector[chave]['registos'].append(registro)
        registos_por_data_sector[chave]['total_entradas'] += entradas_reg
        registos_por_data_sector[chave]['total_saidas'] += saidas_reg
        registos_por_data_sector[chave]['total_saldo'] += saldo_reg
        registos_por_data_sector[chave]['total_combustivel'] += combustivel_reg
        processed_registos.append(registro)

    totais = {
        'total_entradas': sum((getattr(reg, 'entradas_total')() if callable(getattr(reg, 'entradas_total', None)) else Decimal('0')) for reg in processed_registos) if processed_registos else Decimal('0'),
        'total_saidas': sum((getattr(reg, 'saidas_total_incl_combustivel', reg.saidas_total()) for reg in processed_registos)) if processed_registos else Decimal('0'),
        'total_saldo': sum((getattr(reg, 'saldo_liquido_incl_combustivel', reg.saldo_liquido()) for reg in processed_registos)) if processed_registos else Decimal('0'),
        'total_autocarros': len(processed_registos),
        'total_combustivel': sum(getattr(reg, 'combustivel_total', Decimal('0')) for reg in processed_registos) if processed_registos else Decimal('0'),
    }

    context = {
        'registos_agrupados': list(registos_por_data_sector.values()),
        'sectores': Sector.objects.all(),
        'sector_id': sector_id,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'totais': totais,
        'data_hoje': data_hoje,
    }
    return render(request, 'autocarros/relatorios_validados.html', context)

# ----- Relatórios / criação de relatório sector e upload de comprovativos -----
@login_required
def adicionar_relatorio_sector(request):
    """Criar RelatorioSector e os RegistoDiario associados + upload de comprovativos."""
    if request.method == 'POST':
        relatorio_form = RelatorioSectorForm(request.POST)
        multi_file_form = MultiFileForm(request.POST, request.FILES)

        if relatorio_form.is_valid() and multi_file_form.is_valid():
            sector = relatorio_form.cleaned_data['sector']
            data = relatorio_form.cleaned_data['data']
            if RelatorioSector.objects.filter(sector=sector, data=data).exists():
                messages.error(request, f"❌ Já existe um relatório para o setor {sector.nome} na data {data}.")
                return render(request, 'autocarros/adicionar_relatorio_sector.html', {'relatorio_form': relatorio_form, 'multi_file_form': multi_file_form})
            try:
                relatorio = relatorio_form.save()
                arquivos = request.FILES.getlist('arquivos')
                for arquivo in arquivos:
                    if arquivo:
                        ComprovativoRelatorio.objects.create(relatorio=relatorio, arquivo=arquivo, descricao=f"Comprovativo {arquivo.name}")
                autocarros = Autocarro.objects.filter(sector=relatorio.sector)
                registros_criados = []
                for autocarro in autocarros:
                    registro, criado = RegistoDiario.objects.get_or_create(relatorio=relatorio, autocarro=autocarro, data=relatorio.data)
                    if criado:
                        registros_criados.append(registro)
                messages.success(request, f"✅ Relatório para {relatorio.sector.nome} criado com {len(arquivos)} comprovativos!")
                if registros_criados:
                    return redirect('editar_relatorio_sector', pk=registros_criados[0].pk)
                return redirect('listar_registros')
            except Exception as e:
                messages.error(request, f"❌ Erro ao criar relatório: {str(e)}")
        else:
            messages.error(request, "❌ Erro no formulário. Verifique os dados.")
    else:
        relatorio_form = RelatorioSectorForm()
        multi_file_form = MultiFileForm()

    relatorios_recentes = RelatorioSector.objects.select_related('sector').order_by('-data')[:5]
    return render(request, 'autocarros/adicionar_relatorio_sector.html', {'relatorio_form': relatorio_form, 'multi_file_form': multi_file_form, 'relatorios_recentes': relatorios_recentes})

# ----- Edição em massa de registos por sector/data -----
@login_required
def editar_relatorio_sector(request, pk):
    """Editar todos os RegistoDiario de um sector/data (prefix por registo)."""
    registro_base = get_object_or_404(RegistoDiario, pk=pk)
    sector = registro_base.autocarro.sector
    data = registro_base.data
    registros = RegistoDiario.objects.filter(autocarro__sector=sector, data=data).select_related('autocarro')

    # Criar registos faltantes
    autocarros_do_sector = Autocarro.objects.filter(sector=sector)
    autocarros_com_registro = registros.values_list('autocarro_id', flat=True)
    for autocarro in autocarros_do_sector:
        if autocarro.id not in autocarros_com_registro:
            RegistoDiario.objects.create(autocarro=autocarro, data=data)

    registros = RegistoDiario.objects.filter(autocarro__sector=sector, data=data).select_related('autocarro')

    if request.method == "POST":
        for registro in registros:
            form = RegistoDiarioForm(request.POST, instance=registro, prefix=f'registro_{registro.id}')
            if form.is_valid():
                try:
                    if form.cleaned_data.get("validado") and getattr(request.user, "nivel_acesso", "").lower() not in ['admin']:
                        messages.error(request, f"🚫 Você não tem permissão para validar relatórios.")
                        continue
                    form.save()
                except Exception as e:
                    messages.error(request, f"Erro ao salvar registo do autocarro {registro.autocarro.numero}: {str(e)}")
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.warning(request, f"Autocarro {registro.autocarro.numero}, campo {field}: {error}")
        if not any(m.level_tag == 'error' for m in messages.get_messages(request)):
            messages.success(request, f"✅ Registos do sector {sector.nome} do dia {data} atualizados com sucesso!")
            return redirect("listar_registros")

    forms = []
    for registro in registros:
        form = RegistoDiarioForm(instance=registro, prefix=f'registro_{registro.id}')
        forms.append({'form': form, 'registro': registro})

    context = {"sector": sector, "data": data, "forms": forms, "total_registros": registros.count(), "total_autocarros": autocarros_do_sector.count()}
    return render(request, "autocarros/editar_relatorio_sector.html", context)

# ----- Comprovativos (adicionar / deletar) -----
@login_required
def adicionar_comprovativos(request, pk):
    relatorio = get_object_or_404(RelatorioSector, pk=pk)
    if request.method == 'POST':
        arquivos = request.FILES.getlist('arquivos')
        descricao_geral = request.POST.get('descricao_geral', '')
        if arquivos:
            try:
                for arquivo in arquivos:
                    ComprovativoRelatorio.objects.create(relatorio=relatorio, arquivo=arquivo, descricao=descricao_geral or f"Comprovativo {arquivo.name}")
                messages.success(request, f"✅ {len(arquivos)} comprovativo(s) adicionado(s) com sucesso!")
            except Exception as e:
                messages.error(request, f"❌ Erro ao adicionar comprovativos: {str(e)}")
        else:
            messages.warning(request, "⚠️ Nenhum arquivo selecionado.")
        return redirect('editar_relatorio_sector', pk=relatorio.pk)
    return redirect('editar_relatorio_sector', pk=relatorio.pk)

@login_required
def deletar_comprovativo(request, pk):
    comprovativo = get_object_or_404(ComprovativoRelatorio, pk=pk)
    relatorio_pk = comprovativo.relatorio.pk
    if request.method == 'POST':
        try:
            comprovativo.delete()
            messages.success(request, "✅ Comprovativo excluído com sucesso!")
        except Exception as e:
            messages.error(request, f"❌ Erro ao excluir comprovativo: {str(e)}")
    return redirect('editar_relatorio_sector', pk=relatorio_pk)

# ----- Despesas: adicionar / listar / editar / deletar / combustivel -----
@login_required
def adicionar_despesa(request):
    """Adicionar despesa genérica com upload de comprovativos."""
    if request.method == 'POST':
        form = DespesaForm(request.POST)
        multi = MultiFileForm(request.POST, request.FILES)
        if form.is_valid() and multi.is_valid():
            try:
                despesa = form.save()
                arquivos = request.FILES.getlist('arquivos')
                for arquivo in arquivos:
                    if arquivo:
                        Comprovativo.objects.create(despesa=despesa, arquivo=arquivo)
                messages.success(request, '✅ Despesa adicionada com sucesso!')
                return redirect('listar_despesas')
            except Exception as e:
                messages.error(request, f'❌ Erro ao adicionar despesa: {str(e)}')
        else:
            messages.error(request, '❌ Erro no formulário. Verifique os dados.')
    else:
        form = DespesaForm()
        multi = MultiFileForm()
    return render(request, 'despesas/adicionar_despesa.html', {'form': form, 'multi': multi})

@login_required
def selecionar_sector_combustivel(request):
    """Passo inicial para adicionar despesas de combustível (selecionar sector)."""
    if request.method == "POST":
        form = SelecionarSectorCombustivelForm(request.POST)
        if form.is_valid():
            sector = form.cleaned_data["sector"]
            return redirect("adicionar_combustivel", pk=sector.pk)
    else:
        form = SelecionarSectorCombustivelForm()
    return render(request, "despesas/selecionar_sector.html", {"form": form})

@login_required
def adicionar_combustivel(request, pk):
    """Adicionar múltiplas despesas de combustível para todos os autocarros de um sector."""
    sector = get_object_or_404(Sector, pk=pk)
    autocarros = Autocarro.objects.filter(sector=sector).order_by("numero")
    CombustivelFormSet = modelformset_factory(DespesaCombustivel, form=DespesaCombustivelForm, extra=len(autocarros), can_delete=False)

    if request.method == "POST":
        formset = CombustivelFormSet(request.POST, request.FILES, queryset=DespesaCombustivel.objects.none())
        if formset.is_valid():
            try:
                for form, autocarro in zip(formset.forms, autocarros):
                    if form.cleaned_data:
                        inst = form.save(commit=False)
                        inst.sector = sector
                        inst.autocarro = autocarro
                        if not inst.data:
                            inst.data = timezone.now().date()
                        inst.save()
                messages.success(request, "✅ Despesas de combustível adicionadas com sucesso!")
                return redirect("listar_despesas")
            except Exception as e:
                messages.error(request, f"❌ Erro ao adicionar combustível: {str(e)}")
        else:
            messages.error(request, "❌ Erro no formulário. Verifique os dados.")
    else:
        initial_data = [{"sector": sector, "autocarro": a} for a in autocarros]
        formset = CombustivelFormSet(queryset=DespesaCombustivel.objects.none(), initial=initial_data)

    formset_autocarros = zip(formset.forms, autocarros)
    return render(request, "despesas/adicionar_combustivel.html", {"sector": sector, "formset": formset, "formset_autocarros": formset_autocarros})

@login_required
def editar_combustivel(request, pk):
    despesa = get_object_or_404(DespesaCombustivel, pk=pk)
    if request.method == "POST":
        form = DespesaCombustivelForm(request.POST, request.FILES, instance=despesa)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "✅ Despesa de combustível atualizada com sucesso!")
                return redirect("listar_despesas")
            except Exception as e:
                messages.error(request, f"❌ Erro ao atualizar combustível: {str(e)}")
        else:
            messages.error(request, "❌ Erro no formulário. Verifique os dados.")
    else:
        form = DespesaCombustivelForm(instance=despesa)
    return render(request, "despesas/editar_combustivel.html", {"form": form, "despesa": despesa})

@login_required
def deletar_combustivel(request, pk):
    despesa = get_object_or_404(DespesaCombustivel, pk=pk)
    if request.method == "POST":
        try:
            despesa.delete()
            messages.success(request, "✅ Despesa de combustível apagada com sucesso!")
            return redirect("listar_despesas")
        except Exception as e:
            messages.error(request, f"❌ Erro ao apagar combustível: {str(e)}")
    return render(request, "despesas/deletar_combustivel.html", {"despesa": despesa})

@login_required
def listar_despesas(request):
    """Listar despesas (normais + combustível) e mesclar num feed ordenado por data."""
    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    despesas = Despesa.objects.all()
    combustiveis = DespesaCombustivel.objects.all()

    if data_inicio:
        despesas = despesas.filter(data__gte=data_inicio)
        combustiveis = combustiveis.filter(data__gte=data_inicio)
    if data_fim:
        despesas = despesas.filter(data__lte=data_fim)
        combustiveis = combustiveis.filter(data__lte=data_fim)

    todas_despesas = [{"tipo": "normal", "obj": d} for d in despesas] + [{"tipo": "combustivel", "obj": c} for c in combustiveis]
    todas_despesas.sort(key=lambda x: x["obj"].data, reverse=True)

    return render(request, "despesas/listar_despesas.html", {"despesas": todas_despesas, "data_inicio": data_inicio, "data_fim": data_fim})

@login_required
def editar_despesa(request, pk):
    despesa = get_object_or_404(Despesa, pk=pk)
    if request.method == 'POST':
        form = DespesaForm(request.POST, instance=despesa)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, '✅ Despesa atualizada com sucesso!')
                return redirect('listar_despesas')
            except Exception as e:
                messages.error(request, f'❌ Erro ao atualizar despesa: {str(e)}')
        else:
            messages.error(request, '❌ Erro no formulário. Verifique os dados.')
    else:
        form = DespesaForm(instance=despesa)
    return render(request, 'despesas/editar_despesa.html', {'form': form, 'despesa': despesa})

@login_required
def deletar_despesa(request, pk):
    despesa = get_object_or_404(Despesa, pk=pk)
    if request.method == 'POST':
        try:
            despesa.delete()
            messages.success(request, '✅ Despesa deletada com sucesso!')
            return redirect('listar_despesas')
        except Exception as e:
            messages.error(request, f'❌ Erro ao deletar despesa: {str(e)}')
    return render(request, 'despesas/deletar_despesa.html', {'despesa': despesa})

# ----- Dashboards especializados -----
@login_required
def contabilista_financas(request):
    """Resumo financeiro para contabilista: agrega registos e despesas recentes."""
    registos = RegistoDiario.objects.annotate(
        saldo_liquido=ExpressionWrapper(
            (F("normal") + F("alunos") + F("luvu") + F("frete")) -
            (F("alimentacao") + F("parqueamento") + F("taxa") + F("outros")),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
    )

    totais = registos.aggregate(
        total_entradas=Sum(F("normal") + F("alunos") + F("luvu") + F("frete"), output_field=DecimalField()),
        total_saidas=Sum(F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"), output_field=DecimalField()),
        total_saldo=Sum("saldo_liquido"),
    )

    total_despesas_gerais = Despesa.objects.aggregate(total=Sum('valor', output_field=DecimalField()))['total'] or Decimal('0')
    comb_glob = DespesaCombustivel.objects.aggregate(total_valor=Sum('valor', output_field=DecimalField()), total_sobragem=Sum('sobragem_filtros', output_field=DecimalField()), total_lavagem=Sum('lavagem', output_field=DecimalField()))
    total_combustivel_glob = comb_glob.get('total_valor') or Decimal('0')
    total_combustivel_sobragem_glob = comb_glob.get('total_sobragem') or Decimal('0')
    total_combustivel_lavagem_glob = comb_glob.get('total_lavagem') or Decimal('0')

    try:
        orig_saidas = Decimal(totais.get('total_saidas') or 0)
    except Exception:
        orig_saidas = Decimal('0')
    totais['total_saidas'] = orig_saidas + total_despesas_gerais + total_combustivel_glob + total_combustivel_sobragem_glob + total_combustivel_lavagem_glob
    try:
        totais['total_entradas'] = Decimal(totais.get('total_entradas') or 0)
    except Exception:
        totais['total_entradas'] = Decimal('0')
    totais['total_saldo'] = totais['total_entradas'] - totais['total_saidas']

    despesas = Despesa.objects.all().order_by("-data")[:10]
    return render(request, "dashboards/contabilista_financas.html", {"totais": totais, "despesas": despesas})

@login_required
def gerencia_financas(request):
    """Dashboard da gerência com gráficos mensais (Chart.js no template)."""
    registros = (
        RegistoDiario.objects
        .annotate(mes=TruncMonth("data"),
                  entradas=ExpressionWrapper(F("normal") + F("alunos") + F("luvu") + F("frete"), output_field=DecimalField()),
                  saidas=ExpressionWrapper(F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"), output_field=DecimalField()))
        .values("mes")
        .annotate(total_entradas=Sum("entradas"), total_saidas=Sum("saidas"))
        .order_by("mes")
    )

    labels = [r["mes"].strftime("%b/%Y") for r in registros]
    lucros = [(r["total_entradas"] or 0) - (r["total_saidas"] or 0) for r in registros]

    custos_mensais = (
        Despesa.objects
        .annotate(mes=TruncMonth("data"))
        .values("mes")
        .annotate(salarios=Sum("valor", filter=Q(descricao__icontains="salário")), combustivel=Sum("valor", filter=Q(descricao__icontains="combustível")), manutencao=Sum("valor", filter=Q(descricao__icontains="manutenção")))
        .order_by("mes")
    )

    custos_labels = [c["mes"].strftime("%b/%Y") for c in custos_mensais]
    salarios = [c["salarios"] or 0 for c in custos_mensais]
    combustivel = [c["combustivel"] or 0 for c in custos_mensais]
    manutencao = [c["manutencao"] or 0 for c in custos_mensais]

    context = {
        "labels_json": json.dumps(labels),
        "lucros_json": json.dumps(lucros, default=decimal_default),
        "custos_labels_json": json.dumps(custos_labels, default=decimal_default),
        "salarios_json": json.dumps(salarios),
        "combustivel_json": json.dumps(combustivel),
        "manutencao_json": json.dumps(manutencao),
    }
    return render(request, "dashboards/gerencia_financas.html", context)

@login_required
def gerencia_campo(request):
    """Resumo operacional: autocarros, motoristas e estado atual para equipa de campo."""
    try:
        MOTORISTA_MODEL_EXISTS = True if hasattr(models, 'Motorista') else False
    except Exception:
        MOTORISTA_MODEL_EXISTS = False

    if hasattr(Autocarro, "status"):
        autocarros_ativos = Autocarro.objects.filter(status="ativo").count()
        autocarros_inativos = Autocarro.objects.filter(status="inativo").count()
        autocarros_manutencao = Autocarro.objects.filter(status="manutencao").count()
        autocarros_queryset = Autocarro.objects.all().order_by("numero")
    else:
        autocarros_ativos = Autocarro.objects.count()
        autocarros_inativos = Autocarro.objects.count()
        autocarros_manutencao = 0
        autocarros_queryset = Autocarro.objects.all().order_by("numero")

    if MOTORISTA_MODEL_EXISTS:
        motoristas_ativos = Motorista.objects.filter(ativo=True).count()
    else:
        motoristas_ativos = RegistoDiario.objects.exclude(motorista__isnull=True).exclude(motorista__exact="").values("motorista").distinct().count()

    autocarros_map = autocarros_queryset.values("pk", "numero", "modelo", "lat", "lng", "status")

    context = {
        "autocarros_ativos": autocarros_ativos,
        "autocarros_inativos": autocarros_inativos,
        "autocarros_manutencao": autocarros_manutencao,
        "motoristas_ativos": motoristas_ativos,
        "autocarros": list(autocarros_map),
    }
    return render(request, "dashboards/gerencia_campo.html", context)


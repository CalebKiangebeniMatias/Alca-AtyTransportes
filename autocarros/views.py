from datetime import date, datetime
from decimal import Decimal
import json
from django.contrib import messages
from django.db.models import Sum, F, DecimalField, Q
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from urllib.parse import quote_plus
from django.utils.dateparse import parse_date
from django.forms import modelformset_factory
from django.db.models.functions import TruncMonth
from autocarros.decorators import acesso_restrito
from .models import Autocarro, CobradorViagem, Comprovativo, ComprovativoRelatorio, Deposito, DespesaCombustivel, Manutencao, RegistoDiario, Despesa, RegistroKM, RegistroKMItem, RelatorioSector, Sector, Motorista
from .forms import DespesaCombustivelForm, EstadoAutocarroForm, AutocarroForm, DespesaForm, ComprovativoFormSet, ManutencaoForm, MultiFileForm,RegistoDiarioFormSet, RelatorioSectorForm, SectorForm, SectorGestorForm, SelecionarSectorCombustivelForm
from autocarros import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views import View
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserUpdateForm
from .models import CustomUser
from django.utils.text import slugify
from django.contrib.auth.models import User
import json
from django.views.decorators.http import require_POST



# Decorator para só admins poderem associar gestores
@login_required
@acesso_restrito(['admin'])
def admin_required(user):
    return user.is_authenticated and user.is_admin()


@login_required
@acesso_restrito(['admin'])
def associar_gestor(request, sector_id):
    sector = get_object_or_404(Sector, id=sector_id)

    if request.method == "POST":
        form = SectorGestorForm(request.POST, instance=sector)
        if form.is_valid():
            form.save()
            messages.success(request, f'Gestor associado ao setor "{sector.nome}" com sucesso!')
            return redirect('lista_sectores')
    else:
        form = SectorGestorForm(instance=sector)

    return render(request, "autocarros/associar_gestor.html", {
        "form": form,
        "sector": sector,
    })


@login_required
@acesso_restrito(['admin'])
def admin_required(view_func):
    decorated_view = user_passes_test(
        lambda user: user.is_authenticated and user.is_admin(),
        login_url='acesso_negado'
    )(view_func)
    return decorated_view


@login_required
@acesso_restrito(['admin'])
def gestor_required(view_func):
    decorated_view = user_passes_test(
        lambda user: user.is_authenticated and user.is_gestor(),
        login_url='acesso_negado'
    )(view_func)
    return decorated_view


@login_required
def can_edit_required(view_func):
    decorated_view = user_passes_test(
        lambda user: user.is_authenticated and user.can_edit(),
        login_url='acesso_negado'
    )(view_func)
    return decorated_view


class LoginView(View):
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
        else:
            messages.error(request, "Usuário ou senha incorretos.")
            return render(request, 'auth/login.html')


@login_required
@acesso_restrito(['admin'])
def register_user(request):
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
        return redirect('dashboard')  # ou a tua página principal

    niveis = CustomUser.NIVEL_ACESSO_CHOICES
    return render(request, 'auth/register.html', {'niveis': niveis})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
@acesso_restrito(['admin'])
def admin_dashboard(request):
    usuarios = CustomUser.objects.all()
    context = {
        'usuarios': usuarios,
        'total_usuarios': usuarios.count(),
        'usuarios_ativos': usuarios.filter(ativo=True).count(),
    }
    return render(request, 'admin_dashboard.html', context)


@login_required
def perfil(request):
    return render(request, 'autocarros/perfil.html', {'user': request.user})


@login_required
@acesso_restrito(['admin'])
def gerir_usuarios(request):
    usuarios = CustomUser.objects.all().order_by('-date_joined')
    return render(request, 'gerir_usuarios.html', {'usuarios': usuarios})


@login_required
@acesso_restrito(['admin'])
def editar_usuario(request, user_id):
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
    return render(request, 'acesso_negado.html', status=403)


@login_required
@acesso_restrito(['admin'])
def verificar_integridade(request):
    """View para verificar e corrigir problemas de integridade"""
    if not request.user.is_superuser:
        messages.error(request, "❌ Apenas administradores podem acessar esta função.")
        return redirect('listar_registros')
    
    problemas = []
    
    # 🔹 VERIFICAR REGISTROS SEM RELATÓRIO
    registros_sem_relatorio = RegistoDiario.objects.filter(relatorio__isnull=True)
    if registros_sem_relatorio.exists():
        problemas.append(f"❌ {registros_sem_relatorio.count()} registros sem relatório associado")
    
    # 🔹 VERIFICAR RELATÓRIOS SEM REGISTROS
    relatorios_sem_registros = RelatorioSector.objects.filter(registos__isnull=True)
    if relatorios_sem_registros.exists():
        problemas.append(f"❌ {relatorios_sem_registros.count()} relatórios sem registros")
    
    # 🔹 VERIFICAR DUPLICAÇÕES
    from django.db.models import Count
    duplicatas = RegistoDiario.objects.values('relatorio', 'autocarro').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    if duplicatas.exists():
        problemas.append(f"❌ {duplicatas.count()} duplicatas encontradas")
    
    if request.method == "POST" and "corrigir" in request.POST:
        # 🔹 CORRIGIR REGISTROS SEM RELATÓRIO
        for registro in registros_sem_relatorio:
            relatorio_compativel = RelatorioSector.objects.filter(
                sector=registro.autocarro.sector,
                data=registro.data
            ).first()
            
            if relatorio_compativel:
                registro.relatorio = relatorio_compativel
                registro.save()
        
        # 🔹 CRIAR REGISTROS PARA RELATÓRIOS VAZIOS
        for relatorio in relatorios_sem_registros:
            autocarros = Autocarro.objects.filter(sector=relatorio.sector)
            for autocarro in autocarros:
                RegistoDiario.objects.get_or_create(
                    relatorio=relatorio,
                    autocarro=autocarro,
                    defaults={'data': relatorio.data}
                )
        
        messages.success(request, "✅ Problemas de integridade corrigidos!")
        return redirect('verificar_integridade')
    
    context = {
        'problemas': problemas,
        'total_problemas': len(problemas),
    }
    return render(request, "autocarros/verificar_integridade.html", context)


@login_required
def layout_base(request):
    sectores = Sector.objects.all()
    return render(request, "base.html", {"sectores": sectores})


@login_required
@acesso_restrito(['admin'])
def lista_sectores(request):
    sectores = Sector.objects.all().order_by("nome")
    return render(request, "autocarros/lista_sectores.html", {"sectores": sectores})


@login_required
@acesso_restrito(['admin'])
def adicionar_sector(request):
    if request.method == "POST":
        form = SectorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Setor adicionado com sucesso!")
            return redirect("lista_sectores")
        else:
            messages.error(request, "❌ Erro ao adicionar setor. Verifique os dados.")
    else:
        form = SectorForm()
    return render(request, "autocarros/adicionar_sector.html", {"form": form})


@login_required
@acesso_restrito(['admin'])
def editar_sector(request, pk):
    sector = get_object_or_404(Sector, pk=pk)
    if request.method == "POST":
        form = SectorForm(request.POST, instance=sector)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Setor atualizado com sucesso!")
            return redirect("lista_sectores")
        else:
            messages.error(request, "❌ Erro ao atualizar setor. Verifique os dados.")
    else:
        form = SectorForm(instance=sector)
    return render(request, "autocarros/adicionar_sector.html", {"form": form, "editar": True})


@login_required
@acesso_restrito(['admin'])
def apagar_sector(request, pk):
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
def dashboard(request):
    hoje = timezone.now().date()

    # 🔹 Capturar "YYYY-MM" vindo do input type="month"
    mes_param = request.GET.get("mes", hoje.strftime("%Y-%m"))
    try:
        ano, mes = map(int, mes_param.split("-"))
    except ValueError:
        ano, mes = hoje.year, hoje.month

    # 🔹 anos disponíveis
    anos_disponiveis = [
        int(d.year) for d in RegistoDiario.objects.dates("data", "year", order="DESC")
    ]
    if hoje.year not in anos_disponiveis:
        anos_disponiveis.insert(0, hoje.year)

    # 🔹 registos filtrados
    registos = RegistoDiario.objects.filter(
        data__year=ano,
        data__month=mes
    ).select_related("autocarro")

    # 🔹 Combustível por autocarro/data
    combustivel_map_dashboard = {}
    if registos.exists():
        autocarro_ids = set(registos.values_list('autocarro_id', flat=True))
        datas = set(registos.values_list('data', flat=True))
        combustiveis_dash = DespesaCombustivel.objects.filter(
            autocarro_id__in=autocarro_ids,
            data__in=datas
        )
        from collections import defaultdict
        from decimal import Decimal
        agg_dash = defaultdict(lambda: {
            'total_valor': Decimal('0'),
            'total_valor_litros': Decimal('0'),
            'total_sobragem': Decimal('0'),
            'total_lavagem': Decimal('0')
        })
        for c in combustiveis_dash:
            key = f"{c.autocarro_id}_{c.data.isoformat()}"
            agg_dash[key]['total_valor'] += c.valor or Decimal('0')
            agg_dash[key]['total_valor_litros'] += c.valor_litros or Decimal('0')
            agg_dash[key]['total_sobragem'] += c.sobragem_filtros or Decimal('0')
            agg_dash[key]['total_lavagem'] += c.lavagem or Decimal('0')
        combustivel_map_dashboard.update(agg_dash)

    # 🔹 Totais gerais
    total_entradas = registos.aggregate(
        total=Sum(F("normal") + F("alunos") + F("luvu") + F("frete"), output_field=DecimalField())
    )["total"] or Decimal("0")

    total_saidas_registos = registos.aggregate(
        total=Sum(
            F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"),
            output_field=DecimalField()
        )
    )["total"] or Decimal("0")

    total_saidas_despesas = Despesa.objects.filter(
        data__year=ano,
        data__month=mes
    ).aggregate(
        total=Sum("valor", output_field=DecimalField())
    )["total"] or Decimal("0")

    total_combustivel = DespesaCombustivel.objects.filter(
        data__year=ano,
        data__month=mes
    ).aggregate(
        total_valor=Sum('valor', output_field=DecimalField()),
        total_litros=Sum('valor_litros', output_field=DecimalField()),
        total_sobragem=Sum('sobragem_filtros', output_field=DecimalField()),
        total_lavagem=Sum('lavagem', output_field=DecimalField()),
    )

    total_combustivel_valor = total_combustivel.get('total_valor') or Decimal('0')
    total_combustivel_litros = total_combustivel.get('total_litros') or Decimal('0')
    total_combustivel_sobragem = total_combustivel.get('total_sobragem') or Decimal('0')
    total_combustivel_lavagem = total_combustivel.get('total_lavagem') or Decimal('0')

    total_saidas = (
            total_saidas_registos
            + total_saidas_despesas
            + total_combustivel_valor
            + total_combustivel_sobragem
            + total_combustivel_lavagem
    )
    total_resto = total_entradas - total_saidas

    total_variaveis = total_saidas_despesas or Decimal('0')

    total_saidas_sem_variaveis = total_saidas - total_variaveis   # saídas sem as despesas variáveis

    # 🔹 Estatísticas por autocarro
    autocarros_stats = []
    for autocarro in Autocarro.objects.all():
        registos_auto = registos.filter(autocarro=autocarro)
        stats = {
            "autocarro": autocarro,
            "total_km": registos_auto.aggregate(Sum("km_percorridos"))["km_percorridos__sum"] or 0,
            "total_entradas": registos_auto.aggregate(
                total=Sum(F("normal") + F("alunos") + F("luvu") + F("frete"), output_field=DecimalField())
            )["total"] or Decimal('0'),
            "total_saidas": registos_auto.aggregate(
                total=Sum(F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"), output_field=DecimalField())
            )["total"] or Decimal('0'),
            "total_passageiros": registos_auto.aggregate(Sum("numero_passageiros"))["numero_passageiros__sum"] or 0,
            "total_viagens": registos_auto.aggregate(Sum("numero_viagens"))["numero_viagens__sum"] or 0,
        }

        comb_auto = DespesaCombustivel.objects.filter(
            autocarro=autocarro,
            data__year=ano,
            data__month=mes
        ).aggregate(
            total_valor=Sum('valor', output_field=DecimalField()),
            total_litros=Sum('valor_litros', output_field=DecimalField()),
            total_sobragem=Sum('sobragem_filtros', output_field=DecimalField()),
            total_lavagem=Sum('lavagem', output_field=DecimalField()),
        )

        comb_val = comb_auto.get('total_valor') or Decimal('0')
        stats['total_combustivel'] = comb_val
        stats['total_combustivel_litros'] = comb_auto.get('total_litros') or Decimal('0')
        stats['total_combustivel_sobragem'] = comb_auto.get('total_sobragem') or Decimal('0')
        stats['total_combustivel_lavagem'] = comb_auto.get('total_lavagem') or Decimal('0')

        comb_sobr = stats['total_combustivel_sobragem']
        comb_lav = stats['total_combustivel_lavagem']
        stats['total_saidas'] += stats['total_combustivel'] + comb_sobr + comb_lav
        stats["resto"] = stats["total_entradas"] - stats["total_saidas"]

        autocarros_stats.append(stats)

    # 🔹 Calcular o maior saldo (mais lucrativo)
    max_saldo = max((a["resto"] for a in autocarros_stats), default=Decimal('0'))

    # 🔹 Registos recentes
    registos_recentes_qs = registos.order_by("-data")[:10]
    registos_recentes = []
    for reg in registos_recentes_qs:
        key = f"{reg.autocarro_id}_{reg.data.isoformat()}"
        comb = combustivel_map_dashboard.get(key, {})
        reg.combustivel_total = comb.get('total_valor', Decimal('0'))
        reg.combustivel_valor_litros = comb.get('total_valor_litros', Decimal('0'))
        reg.combustivel_sobragem = comb.get('total_sobragem', Decimal('0'))
        reg.combustivel_lavagem = comb.get('total_lavagem', Decimal('0'))
        reg.saidas_total_incl_combustivel = (
            reg.saidas_total() + reg.combustivel_total + reg.combustivel_sobragem + reg.combustivel_lavagem
        )
        reg.saldo_liquido_incl_combustivel = reg.entradas_total() - reg.saidas_total_incl_combustivel
        registos_recentes.append(reg)

    context = {
        "ano": ano,
        "mes": f"{ano}-{mes:02d}",
        "anos_disponiveis": anos_disponiveis,
        "total_entradas": total_entradas,
        "total_saidas": total_saidas,
        "total_saidas_registos": total_saidas_registos,
        "total_saidas_despesas": total_saidas_despesas,
        "total_variaveis": total_variaveis,
        "total_saidas_sem_variaveis": total_saidas_sem_variaveis,
        "total_resto": total_resto,
        "total_combustivel_valor": total_combustivel_valor,
        "total_combustivel_litros": total_combustivel_litros,
        "total_combustivel_sobragem": total_combustivel_sobragem,
        "total_combustivel_lavagem": total_combustivel_lavagem,
        "autocarros_stats": autocarros_stats,
        "registos_recentes": registos_recentes,
        "max_saldo": max_saldo,
    }
    return render(request, "autocarros/dashboard.html", context)

# exportar relatorio

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.utils import timezone
from django.db.models import Sum, F, DecimalField
from django.contrib.humanize.templatetags.humanize import intcomma
from decimal import Decimal
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from datetime import datetime
from .models import RegistoDiario, Despesa, DespesaCombustivel, Autocarro
from .decorators import acesso_restrito
from django.contrib.auth.decorators import login_required


@login_required
@acesso_restrito(['admin'])
def exportar_relatorio_dashboard(request):
    hoje = timezone.now().date()
    mes_param = request.GET.get("mes", hoje.strftime("%Y-%m"))

    try:
        ano, mes = map(int, mes_param.split("-"))
    except ValueError:
        ano, mes = hoje.year, hoje.month

    registos = RegistoDiario.objects.filter(data__year=ano, data__month=mes)

    total_entradas = registos.aggregate(
        total=Sum(F("normal") + F("alunos") + F("luvu") + F("frete"), output_field=DecimalField())
    )["total"] or Decimal("0")

    total_saidas_registos = registos.aggregate(
        total=Sum(F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"), output_field=DecimalField())
    )["total"] or Decimal("0")

    total_saidas_despesas = Despesa.objects.filter(
        data__year=ano, data__month=mes
    ).aggregate(total=Sum("valor", output_field=DecimalField()))["total"] or Decimal("0")

    total_combustivel = DespesaCombustivel.objects.filter(
        data__year=ano, data__month=mes
    ).aggregate(
        total_valor=Sum('valor', output_field=DecimalField()),
        total_sobragem=Sum('sobragem_filtros', output_field=DecimalField()),
        total_lavagem=Sum('lavagem', output_field=DecimalField()),
    )

    total_combustivel_valor = total_combustivel.get('total_valor') or Decimal('0')
    total_combustivel_sobragem = total_combustivel.get('total_sobragem') or Decimal('0')
    total_combustivel_lavagem = total_combustivel.get('total_lavagem') or Decimal('0')

    total_saidas = (
        total_saidas_registos
        + total_saidas_despesas
        + total_combustivel_valor
        + total_combustivel_sobragem
        + total_combustivel_lavagem
    )
    total_resto = total_entradas - total_saidas

    # Estatísticas por autocarro
    autocarros_stats = []
    for autocarro in Autocarro.objects.all():
        registos_auto = registos.filter(autocarro=autocarro)
        if not registos_auto.exists():
            continue

        stats = {
            "autocarro": autocarro,
            "total_km": registos_auto.aggregate(Sum("km_percorridos"))["km_percorridos__sum"] or 0,
            "total_entradas": registos_auto.aggregate(
                total=Sum(F("normal") + F("alunos") + F("luvu") + F("frete"), output_field=DecimalField())
            )["total"] or 0,
            "total_saidas": registos_auto.aggregate(
                total=Sum(F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"), output_field=DecimalField())
            )["total"] or 0,
            "total_passageiros": registos_auto.aggregate(Sum("numero_passageiros"))["numero_passageiros__sum"] or 0,
            "total_viagens": registos_auto.aggregate(Sum("numero_viagens"))["numero_viagens__sum"] or 0,
        }

        comb_auto = DespesaCombustivel.objects.filter(
            autocarro=autocarro, data__year=ano, data__month=mes
        ).aggregate(
            total_valor=Sum('valor', output_field=DecimalField()),
            total_sobragem=Sum('sobragem_filtros', output_field=DecimalField()),
            total_lavagem=Sum('lavagem', output_field=DecimalField()),
        )
        comb_val = comb_auto.get('total_valor') or Decimal('0')
        comb_sobr = comb_auto.get('total_sobragem') or Decimal('0')
        comb_lav = comb_auto.get('total_lavagem') or Decimal('0')

        stats['total_combustivel'] = comb_val
        stats['total_combustivel_litros'] = comb_auto.get('total_litros') or Decimal('0')
        stats['total_combustivel_sobragem'] = comb_auto.get('total_sobragem') or Decimal('0')
        stats['total_combustivel_lavagem'] = comb_auto.get('total_lavagem') or Decimal('0')

        # Incluir combustível, sobragem e lavagem nas saídas por autocarro
        stats['total_saidas'] = stats['total_saidas'] + stats.get('total_combustivel', Decimal('0')) + comb_sobr + comb_lav
        # recalcular resto
        stats["resto"] = stats["total_entradas"] - stats['total_saidas']
        autocarros_stats.append(stats)

    # Criar documento Word
    doc = Document()
    
    # Configurar página para paisagem - FORMA CORRIGIDA
    section = doc.sections[0]
    # Trocar largura e altura para paisagem
    section.page_width = Inches(11.69)  # Largura maior
    section.page_height = Inches(8.27)   # Altura menor
    section.left_margin = section.right_margin = Inches(0.5)
    section.top_margin = section.bottom_margin = Inches(0.5)

    # Cabeçalho profissional
    header_table = doc.add_table(rows=1, cols=3)
    header_table.width = Inches(10.5)
    header_table.autofit = False
    
    # Logo/Ícone (célula esquerda)
    left_cell = header_table.cell(0, 0)
    left_cell.width = Inches(1.5)
    left_para = left_cell.paragraphs[0]
    left_run = left_para.add_run("🚌")
    left_run.font.size = Pt(28)
    left_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Título principal (célula central)
    center_cell = header_table.cell(0, 1)
    center_cell.width = Inches(7)
    center_para = center_cell.paragraphs[0]
    center_run = center_para.add_run(f"RELATÓRIO MENSAL - {mes_param}")
    center_run.font.size = Pt(18)
    center_run.font.bold = True
    center_run.font.color.rgb = RGBColor(13, 27, 42)
    center_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Data (célula direita)
    right_cell = header_table.cell(0, 2)
    right_cell.width = Inches(2)
    right_para = right_cell.paragraphs[0]
    right_run = right_para.add_run(f"{datetime.now().strftime('%d/%m/%Y')}")
    right_run.font.size = Pt(10)
    right_run.font.color.rgb = RGBColor(100, 100, 100)
    right_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph().add_run().add_break()  # Espaço

    # --- RESUMO GERAL EM CARDS HORIZONTAIS ---
    doc.add_heading("RESUMO GERAL DO MÊS", level=2).runs[0].font.color.rgb = RGBColor(27, 42, 73)
    
    tabela_resumo = doc.add_table(rows=2, cols=4)
    tabela_resumo.width = Inches(10.5)
    tabela_resumo.style = "Table Grid"
    
    # Dados dos cards
    cards_data = [
        ("ENTRADAS TOTAIS", f"{intcomma(int(total_entradas))} Kz", "1B4F72"),
        ("DESPESAS TOTAIS", f"{intcomma(int(total_saidas))} Kz", "C0392B"),
        ("SALDO REMANESCENTE", f"{intcomma(int(total_resto))} Kz", "27AE60"),
        ("EFICIÊNCIA", f"{(total_resto/total_entradas*100 if total_entradas > 0 else 0):.1f}%", "8E44AD")
    ]
    
    for i, (titulo, valor, cor) in enumerate(cards_data):
        cell = tabela_resumo.cell(0, i)
        cell.text = titulo
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(10)
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        cell._element.get_or_add_tcPr().append(
            parse_xml(f'<w:shd {nsdecls("w")} w:fill="{cor}"/>')
        )
        
        cell_valor = tabela_resumo.cell(1, i)
        cell_valor.text = valor
        cell_valor.paragraphs[0].runs[0].font.bold = True
        cell_valor.paragraphs[0].runs[0].font.size = Pt(12)
        cell_valor.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph().add_run().add_break()  # Espaço

    # --- DESPESAS ESPECÍFICAS ---
    doc.add_heading("DESPESAS OPERACIONAIS", level=2).runs[0].font.color.rgb = RGBColor(27, 42, 73)
    
    tabela_despesas = doc.add_table(rows=4, cols=3)
    tabela_despesas.width = Inches(10.5)
    tabela_despesas.style = "Table Grid"
    
    # Cabeçalho
    cabecalho_despesas = ["CATEGORIA", "VALOR", "% DO TOTAL"]
    for i, titulo in enumerate(cabecalho_despesas):
        cell = tabela_despesas.cell(0, i)
        cell.text = titulo
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        cell._element.get_or_add_tcPr().append(
            parse_xml(f'<w:shd {nsdecls("w")} w:fill="2C3E50"/>')
        )
    
    # Dados das despesas
    despesas_data = [
        ("Combustível", total_combustivel_valor),
        ("Sopragem de Filtros", total_combustivel_sobragem),
        ("Lavagem", total_combustivel_lavagem),
        ("Outras Despesas", total_saidas_despesas + total_saidas_registos)
    ]
    
    for i, (categoria, valor) in enumerate(despesas_data, 1):
        # Categoria
        cell_cat = tabela_despesas.cell(i, 0)
        cell_cat.text = categoria
        if i % 2 == 0:
            cell_cat._element.get_or_add_tcPr().append(
                parse_xml(f'<w:shd {nsdecls("w")} w:fill="F8F9F9"/>')
            )
        
        # Valor
        cell_val = tabela_despesas.cell(i, 1)
        cell_val.text = f"{intcomma(int(valor))} Kz"
        cell_val.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if i % 2 == 0:
            cell_val._element.get_or_add_tcPr().append(
                parse_xml(f'<w:shd {nsdecls("w")} w:fill="F8F9F9"/>')
            )
        
        # Percentagem
        cell_pct = tabela_despesas.cell(i, 2)
        pct = (valor / total_saidas * 100) if total_saidas > 0 else 0
        cell_pct.text = f"{pct:.1f}%"
        cell_pct.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if i % 2 == 0:
            cell_pct._element.get_or_add_tcPr().append(
                parse_xml(f'<w:shd {nsdecls("w")} w:fill="F8F9F9"/>')
            )

    doc.add_paragraph().add_run().add_break()

    # --- PERFORMANCE POR AUTOCARRO ---
    doc.add_heading("PERFORMANCE POR AUTOCARRO", level=2).runs[0].font.color.rgb = RGBColor(27, 42, 73)
    
    tabela_autocarros = doc.add_table(rows=1, cols=9)
    tabela_autocarros.width = Inches(10.5)
    tabela_autocarros.style = "Table Grid"
    
    # Cabeçalho expandido
    cabecalho_auto = ["Nº", "MODELO", "KM", "ENTRADAS", "DESPESAS", "SALDO", "EFICIÊNCIA", "PASSAGEIROS", "VIAGENS"]
    for i, titulo in enumerate(cabecalho_auto):
        cell = tabela_autocarros.rows[0].cells[i]
        cell.text = titulo
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        cell._element.get_or_add_tcPr().append(
            parse_xml(f'<w:shd {nsdecls("w")} w:fill="1B263B"/>')
        )
    
    # Dados dos autocarros
    for i, stats in enumerate(autocarros_stats, 1):
        row = tabela_autocarros.add_row().cells
        autocarro = stats["autocarro"]
        
        eficiencia = (stats["resto"] / stats["total_entradas"] * 100) if stats["total_entradas"] > 0 else 0
        
        dados_auto = [
            autocarro.numero,
            autocarro.modelo or "-",
            f"{stats['total_km']:,.0f}",
            f"{intcomma(int(stats['total_entradas']))} Kz",
            f"{intcomma(int(stats['total_saidas']))} Kz",
            f"{intcomma(int(stats['resto']))} Kz",
            f"{eficiencia:.1f}%",
            f"{stats['total_passageiros']:,}",
            f"{stats['total_viagens']:,}"
        ]
        
        for j, dado in enumerate(dados_auto):
            row[j].text = dado
            if i % 2 == 0:  # Zebrado
                row[j]._element.get_or_add_tcPr().append(
                    parse_xml(f'<w:shd {nsdecls("w")} w:fill="F8F9F9"/>')
                )
            
            # Alinhamento
            if j in [2, 6, 7, 8]:  # Números
                row[j].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
            elif j in [3, 4, 5]:  # Valores monetários
                row[j].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_paragraph().add_run().add_break()

    # --- RODAPÉ PROFISSIONAL ---
    footer_table = doc.add_table(rows=2, cols=2)
    footer_table.width = Inches(10.5)
    
    # Informações da empresa
    left_cell = footer_table.cell(0, 0)
    left_para = left_cell.paragraphs[0]
    left_para.add_run("Alca&Aty Transportes\n")
    left_para.add_run("Sistema de Gestão de Autocarros\n")
    left_para.add_run("kiangebenimatias4@gmail.com")
    
    # Assinatura
    right_cell = footer_table.cell(0, 1)
    right_para = right_cell.paragraphs[0]
    right_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    right_para.add_run("Relatório gerado automaticamente\n")
    right_para.add_run(f"Em {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
    
    # Linha divisória
    merge_cell = footer_table.cell(1, 0)
    footer_table.cell(1, 1)._element.getparent().remove(footer_table.cell(1, 1)._element)
    merge_cell.merge(footer_table.cell(1, 1))
    merge_para = merge_cell.paragraphs[0]
    merge_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    merge_run = merge_para.add_run("―" * 80)
    merge_run.font.color.rgb = RGBColor(200, 200, 200)
    merge_run.font.size = Pt(8)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    response["Content-Disposition"] = f'attachment; filename="relatorio_mensal_{mes_param}.docx"'
    doc.save(response)
    return response

@login_required
@acesso_restrito(['admin', 'gestor'])
def resumo_sector(request, slug):
    sector_obj = get_object_or_404(Sector, slug=slug)

    nivel = request.user.nivel_acesso.lower()

    # ---- Validação de acesso ----
    if nivel == 'gestor':
        if sector_obj.gestor_id != request.user.id:
            return redirect('acesso_negado')  # 🚫 redireciona

    elif nivel == 'associado':
        if not sector_obj.associados.filter(pk=request.user.pk).exists():
            return redirect('acesso_negado')  # 🚫 redireciona

    elif nivel in ['admin']:
        pass  # acesso total permitido

    else:
        return redirect('acesso_negado')


    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    registos = RegistoDiario.objects.filter(
        autocarro__sector=sector_obj
    ).select_related("autocarro")

    if data_inicio:
        registos = registos.filter(data__gte=parse_date(data_inicio))
    if data_fim:
        registos = registos.filter(data__lte=parse_date(data_fim))

    # Totais gerais
    total_entradas = registos.aggregate(
        total=Sum(F("normal") + F("alunos") + F("luvu") + F("frete"), output_field=DecimalField())
    )["total"] or 0

    total_saidas = registos.aggregate(
        total=Sum(F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"), output_field=DecimalField())
    )["total"] or 0

    total_km = registos.aggregate(Sum("km_percorridos"))["km_percorridos__sum"] or 0
    total_passageiros = registos.aggregate(Sum("numero_passageiros"))["numero_passageiros__sum"] or 0
    total_viagens = registos.aggregate(Sum("numero_viagens"))["numero_viagens__sum"] or 0
    # Agregar despesas de combustível para o filtro
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

    # incluir também sobragem e lavagem nas saídas do sector
    total_saidas_incl_combustivel = total_saidas + total_combustivel_valor + total_combustivel_sobragem + total_combustivel_lavagem

    # Agregar despesas gerais do setor (não confundir com despesas de combustivel)
    despesas_qs = Despesa.objects.filter(sector=sector_obj)
    if data_inicio:
        despesas_qs = despesas_qs.filter(data__gte=parse_date(data_inicio))
    if data_fim:
        despesas_qs = despesas_qs.filter(data__lte=parse_date(data_fim))
    despesas_totais_ag = despesas_qs.aggregate(total=Sum('valor', output_field=DecimalField()))
    total_despesas_sector = despesas_totais_ag.get('total') or Decimal('0')

    # total final de saídas inclui também as despesas do modelo Despesa
    total_saidas_final = total_saidas_incl_combustivel + total_despesas_sector

    resto = total_entradas - total_saidas_final

    # Estatísticas por autocarro
    autocarros_stats = []
    for autocarro in Autocarro.objects.filter(sector=sector_obj):
        registos_auto = registos.filter(autocarro=autocarro)
        stats = {
            "autocarro": autocarro,
            "total_entradas": registos_auto.aggregate(
                total=Sum(F("normal") + F("alunos") + F("luvu") + F("frete"), output_field=DecimalField())
            )["total"] or 0,
            "total_saidas": registos_auto.aggregate(
                total=Sum(F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"), output_field=DecimalField())
            )["total"] or 0,
            "total_km": registos_auto.aggregate(Sum("km_percorridos"))["km_percorridos__sum"] or 0,
            "total_passageiros": registos_auto.aggregate(Sum("numero_passageiros"))["numero_passageiros__sum"] or 0,
            "total_viagens": registos_auto.aggregate(Sum("numero_viagens"))["numero_viagens__sum"] or 0,
        }
        # combustível por autocarro no período
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

        # Ajustar saídas por autocarro para incluir sobragem e lavagem
        stats['total_saidas'] = stats['total_saidas'] + stats.get('total_combustivel', Decimal('0')) + stats.get('total_combustivel_sobragem', Decimal('0')) + stats.get('total_combustivel_lavagem', Decimal('0'))
        stats["resto"] = stats["total_entradas"] - stats["total_saidas"]
        autocarros_stats.append(stats)

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
        # dados para gráfico (Entradas vs Saídas)
        "chart_entradas": float(total_entradas),
        "chart_saidas": float(total_saidas_final),
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        # Despesas do setor (opcionais: filtrar por data)
        "despesas_sector": Despesa.objects.filter(sector=sector_obj)
            .order_by('-data')
            .filter(**({} if not data_inicio else {"data__gte": parse_date(data_inicio)}))
            .filter(**({} if not data_fim else {"data__lte": parse_date(data_fim)})),
    }

    # Montar mensagem para WhatsApp (texto bem formatado)
    try:
        lines = []
        lines.append(f"Resumo do Sector: {sector_obj.nome}")
        periodo = f"{data_inicio or '—'} até {data_fim or '—'}"
        lines.append(f"Período: {periodo}")
        lines.append("")
        lines.append("Totais:")
        lines.append(f"- Entradas: {float(total_entradas):,.2f} Kz")
        lines.append(f"- Saídas (incl. comb.): {float(total_saidas_incl_combustivel):,.2f} Kz")
        lines.append(f"- Combustível: {float(total_combustivel_valor):,.2f} Kz | Litros: {float(total_combustivel_litros):,.2f}")
        lines.append(f"  (Sobragem: {float(total_combustivel_sobragem):,.2f} Kz | Lavagem: {float(total_combustivel_lavagem):,.2f} Kz)")
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
        despesas = context.get('despesas_sector', [])[:10]
        if despesas:
            for d in despesas:
                try:
                    lines.append(f"- {d.data}: {d.descricao} — {float(d.valor):,.2f} Kz ({d.comprovativos.count()} comprov.)")
                except Exception:
                    lines.append(f"- {d.data}: {d.descricao} — {d.valor} Kz")
        else:
            lines.append("- Nenhuma despesa registrada no período.")

        lines.append("")
        from datetime import datetime
        lines.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        whatsapp_text = "\n".join(lines)
        whatsapp_link = "https://api.whatsapp.com/send?text=" + quote_plus(whatsapp_text)
    except Exception:
        whatsapp_text = "Resumo do sector não disponível"
        whatsapp_link = "https://api.whatsapp.com/send?text=" + quote_plus(whatsapp_text)

    # adicionar ao contexto
    context['whatsapp_message'] = whatsapp_text
    context['whatsapp_link'] = whatsapp_link
    return render(request, "autocarros/resumo_sector.html", context)


@login_required
@acesso_restrito(['admin'])
def detalhe_autocarro(request, autocarro_id):
    autocarro = get_object_or_404(Autocarro, id=autocarro_id)
    registos_local = RegistoDiario.objects.filter(autocarro=autocarro)

    entradas = registos_local.aggregate(
        total=Sum(F("normal") + F("alunos") + F("luvu") + F("frete"), output_field=DecimalField())
    )["total"] or 0

    saidas = registos_local.aggregate(
        total=Sum(F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"), output_field=DecimalField())
    )["total"] or 0

    km = registos_local.aggregate(Sum('km_percorridos'))['km_percorridos__sum'] or 0
    passageiros = registos_local.aggregate(Sum('numero_passageiros'))['numero_passageiros__sum'] or 0
    viagens = registos_local.aggregate(Sum('numero_viagens'))['numero_viagens__sum'] or 0
    # Agregar despesas de combustível por autocarro e por data
    combustiveis_qs = DespesaCombustivel.objects.filter(autocarro=autocarro, data__in=registos_local.values_list('data', flat=True))
    from collections import defaultdict
    comb_map = defaultdict(lambda: {
        'total_valor': Decimal('0'),
        'total_valor_litros': Decimal('0'),
        'total_sobragem': Decimal('0'),
        'total_lavagem': Decimal('0'),
    })
    total_combustivel_valor = Decimal('0')
    total_combustivel_litros = Decimal('0')
    total_combustivel_sobragem = Decimal('0')
    total_combustivel_lavagem = Decimal('0')

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

    # Anexar valores agregados a cada registo
    for r in registos_local:
        key = r.data.isoformat()
        agg = comb_map.get(key, {})
        r.combustivel_total = agg.get('total_valor', Decimal('0'))
        r.combustivel_valor_litros = agg.get('total_valor_litros', Decimal('0'))
        r.combustivel_sobragem = agg.get('total_sobragem', Decimal('0'))
        r.combustivel_lavagem = agg.get('total_lavagem', Decimal('0'))
        # saídas e saldo que incluem combustível
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

    # incluir sobragem/lavagem também no total de saídas apresentado
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


# autocarros/views.py
from django.utils import timezone
from datetime import date
from decimal import Decimal
from django.db.models import Q, Sum
from .models import Despesa  # certifique-se que Despesa está importado


# ...existing code...
@login_required
# ...existing code...
@login_required
def listar_registros(request):
    hoje = timezone.now().date()

    # Obter parâmetros de filtro
    sector_id = request.GET.get('sector', '').strip()
    data_inicio = request.GET.get('data_inicio', hoje.isoformat())
    data_fim = request.GET.get('data_fim', hoje.isoformat())

    nivel = request.user.nivel_acesso.lower()

    # 🔹 Determinar o setor (se foi selecionado)
    sector_obj = None
    if sector_id:
        sector_obj = get_object_or_404(Sector, id=sector_id)

    # 🔒 ---- Validação de acesso (ANTES de carregar registros) ----
    if nivel == 'gestor':
        # gestor só pode ver setores que ele gerencia
        if sector_obj:
            if sector_obj.gestor_id != request.user.id:
                return redirect('acesso_negado')
        else:
            # não selecionou setor → filtra só pelos setores do gestor
            sectores_permitidos = Sector.objects.filter(gestor=request.user)

    elif nivel == 'associado':
        # associado só pode ver setores em que está associado
        if sector_obj:
            if not sector_obj.associados.filter(pk=request.user.pk).exists():
                return redirect('acesso_negado')
        else:
            sectores_permitidos = Sector.objects.filter(associados=request.user)

    elif nivel in ['admin', 'superuser']:
        # admin/superuser têm acesso total
        sectores_permitidos = Sector.objects.all()

    else:
        return redirect('acesso_negado')

    # 🔹 ---- Consulta segura ----
    registros = RegistoDiario.objects.select_related('autocarro__sector')

    # Se tiver setor escolhido e validado
    if sector_obj:
        registros = registros.filter(autocarro__sector=sector_obj)
    else:
        # Caso não tenha setor escolhido, mostra só os setores permitidos
        registros = registros.filter(autocarro__sector__in=sectores_permitidos)

    if data_inicio:
        registros = registros.filter(data__gte=data_inicio)

    if data_fim:
        registros = registros.filter(data__lte=data_fim)

    # 🔹 Agregar despesas de combustível por autocarro/data
    combustivel_map = {}
    if registros.exists():
        autocarro_ids = set(registros.values_list('autocarro_id', flat=True))
        datas = set(registros.values_list('data', flat=True))
        combustiveis = DespesaCombustivel.objects.filter(autocarro_id__in=autocarro_ids, data__in=datas)

        from collections import defaultdict
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
                agg[key]['comprovativos'].append(c.comprovativo.url if hasattr(c.comprovativo, 'url') else str(c.comprovativo))

        for k, v in agg.items():
            combustivel_map[k] = v

    # 🔹 Ordenar por data (mais recente primeiro) e sector
    registros = registros.order_by('-data', 'autocarro__sector__nome', 'autocarro__numero')

    # 🔹 Agrupar registros por data e sector e anexar despesas variáveis
    # ...existing code...
    # 🔹 Agrupar registros por data e sector e anexar despesas variáveis
    registros_agrupados = {}
    for registro in registros:
        chave = f"{registro.data.isoformat()}_{registro.autocarro.sector.id}"
        if chave not in registros_agrupados:
            # calcular despesas variáveis DO DIA NO SECTOR (apenas uma vez por grupo)
            try:
                total_variaveis_grupo = Despesa.objects.filter(
                    sector=registro.autocarro.sector,
                    data=registro.data
                ).aggregate(total=Sum('valor'))['total'] or Decimal('0')
                despesas_grupo_qs = Despesa.objects.filter(
                    sector=registro.autocarro.sector,
                    data=registro.data
                ).order_by('-data')
            except Exception:
                total_variaveis_grupo = Decimal('0')
                despesas_grupo_qs = Despesa.objects.none()

            registros_agrupados[chave] = {
                'data': registro.data,
                'sector': registro.autocarro.sector,
                'registos': [],
                'total_entradas': Decimal('0'),
                'total_saidas': Decimal('0'),
                'total_saldo': Decimal('0'),
                'total_variaveis': total_variaveis_grupo,  # agora é por dia+sector
                'despesas_variaveis_do_grupo': list(despesas_grupo_qs),
            }

        # anexar totais de combustível (se existirem) ao objeto registro
        key = f"{registro.autocarro_id}_{registro.data.isoformat()}"
        comb = combustivel_map.get(key)
        if comb:
            if isinstance(comb, dict):
                registro.combustivel_total = comb.get('total_valor', Decimal('0'))
                registro.combustivel_valor_litros = comb.get('total_valor_litros', Decimal('0'))
                registro.combustivel_sobragem = comb.get('total_sobragem_filtros', Decimal('0'))
                registro.combustivel_lavagem = comb.get('total_lavagem', Decimal('0'))
                registro.comprovativos_combustivel = comb.get('comprovativos', [])
            else:
                registro.combustivel_total = getattr(comb, 'valor', Decimal('0')) or Decimal('0')
                registro.combustivel_valor_litros = getattr(comb, 'valor_litros', Decimal('0')) or Decimal('0')
                registro.combustivel_sobragem = getattr(comb, 'sobragem_filtros', Decimal('0')) or Decimal('0')
                registro.combustivel_lavagem = getattr(comb, 'lavagem', Decimal('0')) or Decimal('0')
                registro.comprovativos_combustivel = [comb.comprovativo.url] if getattr(comb, 'comprovativo', None) else []
        else:
            registro.combustivel_total = Decimal('0')
            registro.combustivel_valor_litros = Decimal('0')
            registro.combustivel_sobragem = Decimal('0')
            registro.combustivel_lavagem = Decimal('0')
            registro.comprovativos_combustivel = []

        # atribuir saídas e saldo que incluem combustível
        try:
            registro.saidas_total_incl_combustivel = registro.saidas_total() + registro.combustivel_total + registro.combustivel_sobragem + registro.combustivel_lavagem
        except Exception:
            registro.saidas_total_incl_combustivel = registro.saidas_total()

        try:
            registro.saldo_liquido_incl_combustivel = registro.entradas_total() - registro.saidas_total_incl_combustivel
        except Exception:
            registro.saldo_liquido_incl_combustivel = registro.saldo_liquido()

        try:
            if registro.combustivel_valor_litros and registro.combustivel_valor_litros != Decimal('0'):
                registro.preco_litro = (registro.combustivel_total / registro.combustivel_valor_litros)
            else:
                registro.preco_litro = None
        except Exception:
            registro.preco_litro = None

        # anexar ao registro as despesas do grupo (dia+sector) para exibição
        # OBS: estas despesas são por sector+dia — não adicionamos por registo para evitar duplicação
        registro.despesas_variaveis = registros_agrupados[chave].get('despesas_variaveis_do_grupo', [])
        registro.total_variaveis = registros_agrupados[chave].get('total_variaveis', Decimal('0'))

        # adicionar registro ao agrupamento e atualizar totais do grupo
        registros_agrupados[chave]['registos'].append(registro)
        registros_agrupados[chave]['total_entradas'] += registro.entradas_total()
        registros_agrupados[chave]['total_saidas'] += registro.saidas_total_incl_combustivel
        # NOTA: não somamos registro.total_variaveis por registro (já está no campo group total_variaveis)

        # recalcular saldo parcial do grupo (entradas - saídas (aqui ainda sem variáveis))
        registros_agrupados[chave]['total_saldo'] += registro.entradas_total() - registro.saidas_total_incl_combustivel

    # Depois de montar todos os registos, ajustar cada grupo para incluir as despesas variáveis DO DIA+SECTOR apenas uma vez
    for g in registros_agrupados.values():
        try:
            g_total_variaveis = g.get('total_variaveis', Decimal('0')) or Decimal('0')
            g['total_saidas'] += g_total_variaveis
            # recalcular saldo final do grupo
            g['total_saldo'] = g['total_entradas'] - g['total_saidas']
        except Exception:
            continue

    # 🔹 Calcular totais gerais BASEADOS NOS GRUPOS (evita dupla contagem)
    total_entradas = sum([g['total_entradas'] for g in registros_agrupados.values()]) if registros_agrupados else Decimal('0')
    total_saidas = sum([g['total_saidas'] for g in registros_agrupados.values()]) if registros_agrupados else Decimal('0')
    total_saldo = sum([g['total_saldo'] for g in registros_agrupados.values()]) if registros_agrupados else Decimal('0')

    # total_combustivel: somar valores agregados no combustivel_map (já filtrado pelos registos)
    total_combustivel = sum([v.get('total_valor', Decimal('0')) for v in combustivel_map.values()]) if combustivel_map else Decimal('0')

    # total_variaveis_geral: soma única por grupo (sector+dia)
    total_variaveis_geral = sum([g.get('total_variaveis', Decimal('0')) for g in registros_agrupados.values()]) if registros_agrupados else Decimal('0')

    totais = {
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'total_saldo': total_saldo,
        'total_autocarros': registros.count(),
        'total_combustivel': total_combustivel,
        'total_variaveis': total_variaveis_geral,
    }

    # Preparar link do WhatsApp para cada grupo (mensagem bem formatada)
    for g in registros_agrupados.values():
        try:
            data_str = g['data'].strftime('%d/%m/%Y')
        except Exception:
            data_str = str(g['data'])
        sector_name = g['sector'].nome if g.get('sector') else 'Geral'
        descricao = '-'
        if g['registos'] and getattr(g['registos'][0], 'relatorio', None):
            descricao = g['registos'][0].relatorio.descricao or '-'

      
        parts = []
        parts.append(f"📅 DATA: {data_str}")
        parts.append(f"🏢 RELATÓRIO DO DIA: {sector_name}")
        parts.append("")
        parts.append(f"📝 DESCRIÇÃO: {descricao}")

        # helper local para formatar valores: milhar com ponto e centavos com vírgula
        def fmt_money(valor):
            try:
                d = Decimal(valor)
            except Exception:
                try:
                    return str(valor)
                except Exception:
                    return "0,00"
            sign = '-' if d < 0 else ''
            d = abs(d).quantize(Decimal('0.01'))
            s = f"{d:.2f}"  # "1234.56"
            integer, frac = s.split('.')
            try:
                integer_with_sep = '{:,}'.format(int(integer)).replace(',', '.')
            except Exception:
                integer_with_sep = integer
            return f"{sign}{integer_with_sep},{frac}"

        for reg in g['registos']:
            parts.append("")
            parts.append("__________________________________________")
            parts.append("")
            parts.append(f"🚌 Autocarro: {reg.autocarro.numero} - {reg.autocarro.modelo}")
            parts.append(f"👨‍✈️ Motorista: {reg.motorista or 'N/A'}")
            parts.append(f"👨‍💼 Cobrador Principal: {reg.cobrador_principal or 'N/A'}")
            parts.append(f"👨‍💼 Cobrador Auxiliar: {reg.cobrador_auxiliar or 'N/A'}")
            parts.append("")
            if sector_name.lower() == 'luanda':
                parts.append("✅ Entradas (Manhã/Tarde)")
                parts.append(f"Manhã (Normal): {fmt_money(getattr(reg, 'normal', 0))}kz")
                parts.append(f"Tarde (Alunos): {fmt_money(getattr(reg, 'alunos', 0))}kz")
            else:
                parts.append("✅ Entradas")
                parts.append(f"Normal: {fmt_money(getattr(reg, 'normal', 0))}kz")
                parts.append(f"Alunos: {fmt_money(getattr(reg, 'alunos', 0))}kz")
            parts.append(f"Luvu: {fmt_money(getattr(reg, 'luvu', 0))}kz")
            parts.append(f"Frete: {fmt_money(getattr(reg, 'frete', 0))}kz")
            try:
                entradas_total = reg.entradas_total()
            except Exception:
                entradas_total = Decimal('0')
            parts.append(f"➡️ Total Entradas: {fmt_money(entradas_total)}kz")
            parts.append("")
            parts.append("❌ Saídas")
            parts.append(f"Alimentação: {fmt_money(getattr(reg, 'alimentacao', 0))}kz")
            parts.append(f"Parqueamento: {fmt_money(getattr(reg, 'parqueamento', 0))}kz")
            parts.append(f"Taxa: {fmt_money(getattr(reg, 'taxa', 0))}kz")
            parts.append(f"Outros: {fmt_money(getattr(reg, 'outros', 0))}kz")
            try:
                parts.append(f"Combustível (valor): {fmt_money(getattr(reg, 'combustivel_total', 0))}")
            except Exception:
                parts.append(f"Combustível (valor): {fmt_money(0)}")
            try:
                parts.append(f"Sobragem/Filtros: {fmt_money(getattr(reg, 'combustivel_sobragem', 0))}")
            except Exception:
                parts.append(f"Sobragem/Filtros: {fmt_money(0)}")
            try:
                parts.append(f"Lavagem: {fmt_money(getattr(reg, 'combustivel_lavagem', 0))}")
            except Exception:
                parts.append(f"Lavagem: {fmt_money(0)}")
            try:
                parts.append(f"Despesas Variáveis (total): {fmt_money(getattr(reg, 'total_variaveis', 0))}")
            except Exception:
                parts.append(f"Despesas Variáveis (total): {fmt_money(0)}")
            try:
                saidas_total = getattr(reg, 'saidas_total_incl_combustivel', reg.saidas_total()) + (getattr(reg, 'total_variaveis', Decimal('0')) or Decimal('0'))
            except Exception:
                saidas_total = Decimal('0')
            parts.append(f"➡️ Total Saídas: {fmt_money(saidas_total)}kz")
            parts.append("")
            parts.append("📊 Outros Dados")
            parts.append(f"Kms: {getattr(reg, 'km_percorridos', 0)}")
            parts.append(f"Passageiros: {getattr(reg, 'numero_passageiros', 0)}")
            parts.append(f"Viagens: {getattr(reg, 'numero_viagens', 0)}")
            parts.append("")
            try:
                saldo = getattr(reg, 'saldo_apos_variaveis', getattr(reg, 'saldo_liquido_incl_combustivel', reg.saldo_liquido()))
            except Exception:
                saldo = Decimal('0')
            parts.append(f"💰 Saldo Liquído: {fmt_money(saldo)}kz")

        parts.append("")
        parts.append("__________________________________________")
        parts.append("")
        parts.append("📊 Resumo")
        parts.append("")
        parts.append(f"✅ Entrada Geral: {fmt_money(total_entradas)}kz")
        parts.append("")
        parts.append(f"❌ Saida Geral: {fmt_money(total_saidas)}kz")
        parts.append("")
        parts.append(f"💰 Liquído Geral: {fmt_money(total_saldo)}kz")
        parts.append("")
        parts.append(f"Suporte tecnico: @kiangebenimatias4@gmail.com, +244 944 790 744 (WhatsApp)")

        message = '\n'.join(parts)
        g['whatsapp_link'] = f"https://wa.me/?text={quote_plus(message)}"

    # 🔹 Obter sectores para o filtro
    sectores = Sector.objects.all()

    context = {
        'registros_agrupados': list(registros_agrupados.values()),
        'sectores': sectores,
        'sector_id': sector_id,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'totais': totais,
        'hoje': hoje,
    }
    context['combustivel_map'] = combustivel_map

    return render(request, 'autocarros/listar_registros.html', context)


@login_required
def deletar_registros_sector_data(request, sector_id, data):
    sector = get_object_or_404(Sector, pk=sector_id)
    data_obj = parse_date(data)
    if not data_obj:
        messages.error(request, '❌ Data inválida.')
        return redirect('listar_registros')
    if request.method == 'POST':
        try:
            # Excluir todos os registros do setor e data
            RegistoDiario.objects.filter(autocarro__sector=sector, data=data_obj).delete()
            # Excluir o relatório do setor e data
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
    """Marca o relatório como concluído"""
    relatorio = get_object_or_404(RelatorioSector, pk=pk)
    
    if request.method == 'POST':
        try:
            # 🔹 Aqui você pode adicionar lógica adicional se necessário
            messages.success(request, f"✅ Relatório de {relatorio.sector.nome} concluído com sucesso!")
        except Exception as e:
            messages.error(request, f"❌ Erro ao concluir relatório: {str(e)}")
    
    return redirect('listar_registros')


@login_required
@acesso_restrito(['admin'])
def validar_relatorio(request, pk):
    """Marca o relatório como validado pelo supervisor — só admin pode validar."""
    relatorio = get_object_or_404(RelatorioSector, pk=pk)

    # Verificação redundante/explicita para evitar inconsistências no campo nivel_acesso
    nivel = getattr(request.user, "nivel_acesso", "") or ""
    if not (hasattr(request.user, "is_admin") and request.user.is_admin()) and nivel.lower() != "admin":
        messages.error(request, "❌ Acesso negado. Apenas administradores podem validar relatórios.")
        return redirect('acesso_negado')

    if request.method == 'POST':
        try:
            # marcar como validado (implemente a lógica real aqui, ex: relatorio.validado = True; relatorio.save())
            # Exemplo genérico:
            if hasattr(relatorio, "validado"):
                relatorio.validado = True
                relatorio.save()
            messages.success(request, f"✅ Relatório de {relatorio.sector.nome} validado com sucesso!")
        except Exception as e:
            messages.error(request, f"❌ Erro ao validar relatório: {str(e)}")

    return redirect('listar_registros')


@login_required
def relatorios_validados(request):
    # Obter parâmetros de filtro
    sector_id = request.GET.get('sector', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    
    # Data padrão: hoje
    data_hoje = timezone.now().date()
    
    # 🔹 CORRIGIR a query - agora trabalhamos diretamente com RegistoDiario
    registos_validados = RegistoDiario.objects.filter(validado=True)
    
    # Aplicar filtros
    if sector_id:
        registos_validados = registos_validados.filter(autocarro__sector_id=sector_id)
    
    if data_inicio:
        registos_validados = registos_validados.filter(data__gte=data_inicio)
    
    if data_fim:
        registos_validados = registos_validados.filter(data__lte=data_fim)
    
    # Se não há filtros de data, mostrar apenas dados do dia atual
    if not data_inicio and not data_fim:
        registos_validados = registos_validados.filter(data=data_hoje)
        data_inicio = data_hoje.isoformat()
        data_fim = data_hoje.isoformat()
    
    # Agregar despesas de combustível para os registos validados (por autocarro+data)
    combustivel_map_validados = {}
    if registos_validados.exists():
        autocarro_ids = set(registos_validados.values_list('autocarro_id', flat=True))
        datas = set(registos_validados.values_list('data', flat=True))
        combustiveis_val = DespesaCombustivel.objects.filter(autocarro_id__in=autocarro_ids, data__in=datas)
        from collections import defaultdict
        agg_val = defaultdict(lambda: {
            'total_valor': Decimal('0'),
            'total_valor_litros': Decimal('0'),
            'total_sobragem': Decimal('0'),
            'total_lavagem': Decimal('0'),
        })
        for c in combustiveis_val:
            key = f"{c.autocarro_id}_{c.data.isoformat()}"
            agg_val[key]['total_valor'] += c.valor or Decimal('0')
            agg_val[key]['total_valor_litros'] += c.valor_litros or Decimal('0')
            agg_val[key]['total_sobragem'] += c.sobragem_filtros or Decimal('0')
            agg_val[key]['total_lavagem'] += c.lavagem or Decimal('0')
        for k, v in agg_val.items():
            combustivel_map_validados[k] = v

    # Agrupar registos por data e sector para exibição e anexar combustíveis
    registos_por_data_sector = {}
    processed_registos = []
    for registro in registos_validados.select_related('autocarro__sector'):
        # anexar agregados de combustível ao registro para uso nos totais
        key = f"{registro.autocarro_id}_{registro.data.isoformat()}"
        comb = combustivel_map_validados.get(key, {})
        registro.combustivel_total = comb.get('total_valor', Decimal('0'))
        registro.combustivel_valor_litros = comb.get('total_valor_litros', Decimal('0'))
        registro.combustivel_sobragem = comb.get('total_sobragem', Decimal('0'))
        registro.combustivel_lavagem = comb.get('total_lavagem', Decimal('0'))
        # saídas e saldo que incluem combustível
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

        # atualizar totais do grupo usando valores já anexados ao registro
        try:
            entradas_reg = registro.entradas_total()
        except Exception:
            entradas_reg = Decimal('0')
        # garantir Decimal
        try:
            entradas_reg = Decimal(entradas_reg)
        except Exception:
            entradas_reg = Decimal('0')

        try:
            saidas_reg = getattr(registro, 'saidas_total_incl_combustivel', registro.saidas_total())
        except Exception:
            saidas_reg = Decimal('0')
        try:
            saidas_reg = Decimal(saidas_reg)
        except Exception:
            saidas_reg = Decimal('0')

        try:
            saldo_reg = getattr(registro, 'saldo_liquido_incl_combustivel', registro.saldo_liquido())
        except Exception:
            saldo_reg = Decimal('0')
        try:
            saldo_reg = Decimal(saldo_reg)
        except Exception:
            saldo_reg = Decimal('0')

        combustivel_reg = getattr(registro, 'combustivel_total', Decimal('0'))
        try:
            combustivel_reg = Decimal(combustivel_reg)
        except Exception:
            combustivel_reg = Decimal('0')

        registos_por_data_sector[chave]['registos'].append(registro)
        registos_por_data_sector[chave]['total_entradas'] += entradas_reg
        registos_por_data_sector[chave]['total_saidas'] += saidas_reg
        registos_por_data_sector[chave]['total_saldo'] += saldo_reg
        registos_por_data_sector[chave]['total_combustivel'] += combustivel_reg
        processed_registos.append(registro)
    
    # Calcular totais
    # Calcular totais a partir dos registros já processados (com combustíveis anexados)
    totais = {
        'total_entradas': sum(getattr(reg, 'entradas_total')() if callable(getattr(reg, 'entradas_total', None)) else Decimal('0') for reg in processed_registos) if processed_registos else Decimal('0'),
        'total_saidas': sum(getattr(reg, 'saidas_total_incl_combustivel', reg.saidas_total()) for reg in processed_registos) if processed_registos else Decimal('0'),
        'total_saldo': sum(getattr(reg, 'saldo_liquido_incl_combustivel', reg.saldo_liquido()) for reg in processed_registos) if processed_registos else Decimal('0'),
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


@login_required
def adicionar_relatorio_sector(request):
    if request.method == 'POST':
        relatorio_form = RelatorioSectorForm(request.POST)
        
        # 🔹 USAR O FORMULÁRIO SIMPLIFICADO
        multi_file_form = MultiFileForm(request.POST, request.FILES)
        
        if relatorio_form.is_valid() and multi_file_form.is_valid():
            # 🔹 VERIFICAR SE JÁ EXISTE RELATÓRIO PARA ESTE SETOR NA DATA
            sector = relatorio_form.cleaned_data['sector']
            data = relatorio_form.cleaned_data['data']
            
            if RelatorioSector.objects.filter(sector=sector, data=data).exists():
                messages.error(request, f"❌ Já existe um relatório para o setor {sector.nome} na data {data}.")
                return render(request, 'autocarros/adicionar_relatorio_sector.html', {
                    'relatorio_form': relatorio_form,
                    'multi_file_form': multi_file_form
                })
            
            try:
                # Salvar o relatório
                relatorio = relatorio_form.save()
                
                # 🔹 SALVAR MÚLTIPLOS ARQUIVOS
                arquivos = request.FILES.getlist('arquivos')
                for arquivo in arquivos:
                    if arquivo:  # Verificar se o arquivo não está vazio
                        ComprovativoRelatorio.objects.create(
                            relatorio=relatorio,
                            arquivo=arquivo,
                            descricao=f"Comprovativo {arquivo.name}"
                        )
                
                # Criar registos para cada autocarro do sector
                autocarros = Autocarro.objects.filter(sector=relatorio.sector)
                registros_criados = []
                for autocarro in autocarros:
                    registro, criado = RegistoDiario.objects.get_or_create(
                        relatorio=relatorio,
                        autocarro=autocarro,
                        data=relatorio.data
                    )
                    if criado:
                        registros_criados.append(registro)

                messages.success(request, f"✅ Relatório para {relatorio.sector.nome} criado com {len(arquivos)} comprovativos!")
                # Redirecionar para o primeiro registro criado
                if registros_criados:
                    return redirect('editar_relatorio_sector', pk=registros_criados[0].pk)
                else:
                    return redirect('listar_registros')
                
            except Exception as e:
                messages.error(request, f"❌ Erro ao criar relatório: {str(e)}")
        else:
            messages.error(request, "❌ Erro no formulário. Verifique os dados.")
    else:
        relatorio_form = RelatorioSectorForm()
        multi_file_form = MultiFileForm()

    # Relatórios recentes para referência
    relatorios_recentes = RelatorioSector.objects.select_related('sector').order_by('-data')[:5]

    return render(request, 'autocarros/adicionar_relatorio_sector.html', {
        'relatorio_form': relatorio_form,
        'multi_file_form': multi_file_form,
        'relatorios_recentes': relatorios_recentes
    })


# autocarros/views.py
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from .models import RegistoDiario, Autocarro, Sector
from .forms import RegistoDiarioForm

@login_required
def editar_relatorio_sector(request, pk):
    """
    View para editar registos diários agrupados por sector e data
    Agora trabalhamos diretamente com RegistoDiario em vez de RelatorioSector
    """
    
    # 🔹 OBTER TODOS OS REGISTOS DO MESMO SETOR E DATA
    # Primeiro, precisamos identificar o sector e data baseados no ID do registo
    registro_base = get_object_or_404(RegistoDiario, pk=pk)
    sector = registro_base.autocarro.sector
    data = registro_base.data
    
    # 🔹 OBTER TODOS OS REGISTOS DO MESMO SETOR E DATA
    registros = RegistoDiario.objects.filter(
        autocarro__sector=sector,
        data=data
    ).select_related('autocarro')
    
    # 🔹 CRIAR REGISTROS FALTANTES PARA AUTOCARROS DO SETOR
    autocarros_do_sector = Autocarro.objects.filter(sector=sector)
    autocarros_com_registro = registros.values_list('autocarro_id', flat=True)
    
    for autocarro in autocarros_do_sector:
        if autocarro.id not in autocarros_com_registro:
            RegistoDiario.objects.create(
                autocarro=autocarro,
                data=data,
                # Campos padrão podem ser adicionados aqui
            )
    
    # 🔹 ATUALIZAR A QUERY COM OS NOVOS REGISTROS
    registros = RegistoDiario.objects.filter(
        autocarro__sector=sector,
        data=data
    ).select_related('autocarro')

    if request.method == "POST":
        # Processar cada formulário individualmente
        for registro in registros:
            form = RegistoDiarioForm(
                request.POST, 
                instance=registro,
                prefix=f'registro_{registro.id}'
            )
            
            if form.is_valid():
                try:
                    # 🔒 Verifica se o usuário tentou validar sem permissão
                    if form.cleaned_data.get("validado") and request.user.nivel_acesso not in ['admin']:
                        messages.error(request, f"🚫 Você não tem permissão para validar relatórios.")
                        continue  # não salva esse registro

                    form.save()

                except Exception as e:
                    messages.error(
                        request, 
                        f"Erro ao salvar registo do autocarro {registro.autocarro.numero}: {str(e)}"
                    )
            else:
                # Mostrar erros de validação
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.warning(
                            request, 
                            f"Autocarro {registro.autocarro.numero}, campo {field}: {error}"
                        )
        
        # Verificar se houve algum erro antes de redirecionar
        if not any(message.tags == 'error' for message in messages.get_messages(request)):
            messages.success(
                request, 
                f"✅ Registos do sector {sector.nome} do dia {data} atualizados com sucesso!"
            )
            return redirect("listar_registros")
    
    # Preparar os formulários para exibição
    forms = []
    for registro in registros:
        form = RegistoDiarioForm(
            instance=registro,
            prefix=f'registro_{registro.id}'
        )
        forms.append({
            'form': form,
            'registro': registro
        })

    context = {
        "sector": sector,
        "data": data,
        "forms": forms,
        "total_registros": registros.count(),
        "total_autocarros": autocarros_do_sector.count()
    }
    
    return render(request, "autocarros/editar_relatorio_sector.html", context)


@login_required
def adicionar_comprovativos(request, pk):
    """Adicionar comprovativos a um relatório existente"""
    relatorio = get_object_or_404(RelatorioSector, pk=pk)
    
    if request.method == 'POST':
        arquivos = request.FILES.getlist('arquivos')
        descricao_geral = request.POST.get('descricao_geral', '')
        
        if arquivos:
            try:
                for arquivo in arquivos:
                    ComprovativoRelatorio.objects.create(
                        relatorio=relatorio,
                        arquivo=arquivo,
                        descricao=descricao_geral or f"Comprovativo {arquivo.name}"
                    )
                
                messages.success(request, f"✅ {len(arquivos)} comprovativo(s) adicionado(s) com sucesso!")
            except Exception as e:
                messages.error(request, f"❌ Erro ao adicionar comprovativos: {str(e)}")
        else:
            messages.warning(request, "⚠️ Nenhum arquivo selecionado.")
        
        return redirect('editar_relatorio_sector', pk=relatorio.pk)
    
    return redirect('editar_relatorio_sector', pk=relatorio.pk)


@login_required
def deletar_comprovativo(request, pk):
    """Deletar um comprovativo específico"""
    comprovativo = get_object_or_404(ComprovativoRelatorio, pk=pk)
    relatorio_pk = comprovativo.relatorio.pk
    
    if request.method == 'POST':
        try:
            comprovativo.delete()
            messages.success(request, "✅ Comprovativo excluído com sucesso!")
        except Exception as e:
            messages.error(request, f"❌ Erro ao excluir comprovativo: {str(e)}")
    
    return redirect('editar_relatorio_sector', pk=relatorio_pk)


@login_required
def deletar_relatorio_sector(request, pk):
    relatorio = get_object_or_404(RelatorioSector, pk=pk)

    if request.method == "POST":
        try:
            relatorio.delete()
            messages.success(request, "✅ Relatório do setor apagado com sucesso!")
            return redirect("listar_registros")
        except Exception as e:
            messages.error(request, f"❌ Erro ao apagar relatório: {str(e)}")

    return render(request, "autocarros/deletar_relatorio_sector.html", {
        "relatorio": relatorio
    })


@login_required
def listar_autocarros(request):
    autocarros = Autocarro.objects.all().order_by('numero')
    return render(request, 'autocarros/listar_autocarros.html', {'autocarros': autocarros})


@login_required
def alterar_status_autocarro(request, pk):
    autocarro = get_object_or_404(Autocarro, pk=pk)
    if request.method == "POST":
        novo_status = request.POST.get("status")
        if novo_status in dict(Autocarro._meta.get_field("status").choices):
            autocarro.status = novo_status
            autocarro.save()
            messages.success(request, f"✅ Status do autocarro {autocarro.numero} atualizado para {autocarro.get_status_display()}.")
        else:
            messages.error(request, "❌ Status inválido.")
    return redirect("listar_autocarros")


@login_required
def cadastrar_autocarro(request):
    if request.method == 'POST':
        form = AutocarroForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, '✅ Autocarro cadastrado com sucesso!')
                return redirect('listar_autocarros')
            except Exception as e:
                messages.error(request, f'❌ Erro ao cadastrar autocarro: {str(e)}')
        else:
            messages.error(request, '❌ Erro no formulário. Verifique os dados.')
    else:
        form = AutocarroForm()
    return render(request, 'autocarros/cadastrar_autocarro.html', {'form': form})


@login_required
# Atualizar estado do autocarro
def atualizar_estado(request):
    if request.method == "POST":
        form = EstadoAutocarroForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "✅ Estado do autocarro atualizado com sucesso!")
                return redirect("listar_autocarros")
            except Exception as e:
                messages.error(request, f"❌ Erro ao atualizar estado: {str(e)}")
        else:
            messages.error(request, "❌ Erro no formulário. Verifique os dados.")
    else:
        form = EstadoAutocarroForm()
    return render(request, "autocarros/atualizar_estado.html", {"form": form})


@login_required
# editar autocarro
def editar_autocarro(request, pk):
    autocarro = get_object_or_404(Autocarro, pk=pk)
    if request.method == 'POST':
        form = AutocarroForm(request.POST, instance=autocarro)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, '✅ Autocarro atualizado com sucesso!')
               
                return redirect('listar_autocarros')
            except Exception as e:
                messages.error(request, f'❌ Erro ao atualizar autocarro: {str(e)}')
        else:
            messages.error(request, '❌ Erro no formulário. Verifique os dados.')
    else:
        form = AutocarroForm(instance=autocarro)
    return render(request, 'autocarros/editar_autocarro.html', {'form': form, 'autocarro': autocarro})


@login_required
# deletar autocarro
def deletar_autocarro(request, pk):
    autocarro = get_object_or_404(Autocarro, pk=pk)
    if request.method == 'POST':
        try:
            autocarro.delete()
            messages.success(request, '✅ Autocarro deletado com sucesso!')
            return redirect('listar_autocarros')
        except Exception as e:
            messages.error(request, f'❌ Erro ao deletar autocarro: {str(e)}')
    return render(request, 'autocarros/deletar_autocarro.html', {'autocarro': autocarro})


# ---------- Despesa Combustível Views ----------#
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import DespesaCombustivel, Autocarro


@login_required
# Listar despesas de combustível
def listar_combustivel(request):
    """
    Listagem de despesas de combustível (filtro por intervalo de datas e por autocarro).
    """
    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")
    autocarro_id = request.GET.get("autocarro")

    qs = DespesaCombustivel.objects.select_related("autocarro", "autocarro__sector").all()
    if data_inicio:
        qs = qs.filter(data__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data__lte=data_fim)
    if autocarro_id:
        qs = qs.filter(autocarro_id=autocarro_id)

    qs = qs.order_by("-data")

    autocarros = Autocarro.objects.all().order_by("numero")

    context = {
        "combustiveis": qs,
        "autocarros": autocarros,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "autocarro_selected": autocarro_id,
    }
    return render(request, "despesas/listar_combustivel.html", context)


@login_required
# selecionar sector antes de adicionar despesas de combustível
def selecionar_sector_combustivel(request):
    if request.method == "POST":
        form = SelecionarSectorCombustivelForm(request.POST)
        if form.is_valid():
            sector = form.cleaned_data["sector"]
            return redirect("adicionar_combustivel", pk=sector.pk)
    else:
        form = SelecionarSectorCombustivelForm()

    return render(request, "despesas/selecionar_sector.html", {"form": form})


@login_required
# adicionar despesas de combustível para todos os autocarros de um sector
def adicionar_combustivel(request, pk):
    sector = get_object_or_404(Sector, pk=pk)
    autocarros = Autocarro.objects.filter(sector=sector).order_by("numero")

    CombustivelFormSet = modelformset_factory(
        DespesaCombustivel,
        form=DespesaCombustivelForm,
        extra=len(autocarros),
        can_delete=False
    )

    if request.method == "POST":
        formset = CombustivelFormSet(
            request.POST,
            request.FILES,
            queryset=DespesaCombustivel.objects.none()
        )
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
        formset = CombustivelFormSet(
            queryset=DespesaCombustivel.objects.none(),
            initial=initial_data
        )

    formset_autocarros = zip(formset.forms, autocarros)

    return render(request, "despesas/adicionar_combustivel.html", {
        "sector": sector,
        "formset": formset,
        "formset_autocarros": formset_autocarros,
    })


@login_required
# editar despesas de combustível
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

    return render(request, "despesas/editar_combustivel.html", {
        "form": form,
        "despesa": despesa,
    })


@login_required
# deletar despesas de combustível
def deletar_combustivel(request, pk):
    despesa = get_object_or_404(DespesaCombustivel, pk=pk)

    if request.method == "POST":
        try:
            despesa.delete()
            messages.success(request, "✅ Despesa de combustível apagada com sucesso!")
            return redirect("listar_despesas")
        except Exception as e:
            messages.error(request, f"❌ Erro ao apagar combustível: {str(e)}")

    return render(request, "despesas/deletar_combustivel.html", {
        "despesa": despesa,
    })


# ------------ Despesas normais ou variavéis ----------#
@login_required
# Despesas 'normais ou variáveis' (não combustível)
def listar_despesas(request):
    """
    Listar apenas despesas 'normais' (classificadas aqui como 'variáveis').
    Filtra por intervalo de datas se fornecido.
    """
    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    despesas_qs = Despesa.objects.all()
    if data_inicio:
        despesas_qs = despesas_qs.filter(data__gte=data_inicio)
    if data_fim:
        despesas_qs = despesas_qs.filter(data__lte=data_fim)

    # Ordenar por data decrescente e empacotar para o template
    despesas_qs = despesas_qs.order_by('-data')
    despesas = [{"tipo": "variavel", "obj": d} for d in despesas_qs]

    return render(request, "despesas/listar_despesas.html", {"despesas": despesas, "data_inicio": data_inicio, "data_fim": data_fim})


@login_required
# adicionar despesas 'normais ou variáveis'
def adicionar_despesa(request):
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
# editar despesas 'normais ou variáveis'
def editar_despesa(request, pk):
    try:
        despesa = Despesa.objects.get(pk=pk)
    except Despesa.DoesNotExist:
        messages.error(request, "A despesa que tentou editar não existe ou foi removida.")
        return redirect('listar_despesas')
    
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
# deletar despesas 'normais ou variáveis'
def deletar_despesa(request, pk):
    try:
        despesa = Despesa.objects.get(pk=pk)
    except Despesa.DoesNotExist:
        messages.error(request, "A despesa que tentou eliminar não existe ou já foi removida.")
        return redirect('listar_despesas')

    if request.method == 'POST':
        try:
            despesa.delete()
            messages.success(request, "✅ Despesa eliminada com sucesso!")
            return redirect('listar_despesas')
        except Exception as e:
            messages.error(request, f"❌ Erro ao eliminar a despesa: {str(e)}")

    return render(request, 'despesas/deletar_despesa.html', {'despesa': despesa})


# ---------- Depósitos Views ----------#

@login_required
@acesso_restrito(['admin'])
def depositos_view(request):
    """
    Página com abas: Registrar depósito, Listar depósitos, Totais por sector.
    """
    sectores = Sector.objects.all().order_by('nome')
    ultimos = Deposito.objects.select_related('sector','responsavel').order_by('-data_deposito')[:20]
    return render(request, 'depositos/depositos.html', {'sectores': sectores, 'ultimos': ultimos})


@login_required
@require_POST
@acesso_restrito(['admin'])
def depositos_save(request):
    """
    Salvar depósito via POST JSON ou form-POST.
    Aceita JSON no body ou form-data.
    """
    # detectar JSON independentemente de charset
    content_type = (request.META.get('CONTENT_TYPE') or request.content_type or '').lower()
    if content_type.startswith('application/json'):
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest('JSON inválido')
        sector_id = data.get('sector_id')
        data_deposito = data.get('data_deposito')
        valor = data.get('valor')
        observacao = data.get('observacao', '')
    else:
        sector_id = request.POST.get('sector_id')
        data_deposito = request.POST.get('data_deposito')
        valor = request.POST.get('valor')
        observacao = request.POST.get('observacao', '')

    if not sector_id or not valor:
        return JsonResponse({'ok': False, 'error': 'sector_id e valor obrigatórios'}, status=400)
    try:
        sector = Sector.objects.get(pk=sector_id)
    except Sector.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Sector não encontrado'}, status=404)

    try:
        valor_dec = Decimal(str(valor))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Valor inválido'}, status=400)

    dep = Deposito.objects.create(
        sector=sector,
        data_deposito=data_deposito or None,
        valor=valor_dec,
        observacao=observacao,
        responsavel=request.user
    )
    return JsonResponse({'ok': True, 'deposito_id': dep.id, 'valor': str(dep.valor), 'data_deposito': dep.data_deposito.isoformat() if dep.data_deposito else None})


@login_required
@acesso_restrito(['admin'])
def depositos_list(request):
    """
    API para listar depósitos (opcional filtro por sector) e retornar total.
    GET params: sector_id (opcional), limit (opcional)
    """
    qs = Deposito.objects.select_related('sector','responsavel').all()
    sector_id = request.GET.get('sector_id')
    if sector_id:
        qs = qs.filter(sector_id=sector_id)
    limit = request.GET.get('limit')
    if limit:
        try:
            qs = qs[:int(limit)]
        except Exception:
            pass
    total = qs.aggregate(total_valor=Sum('valor'))['total_valor'] or Decimal('0.00')
    items = []
    for d in qs.order_by('-data_deposito')[:200]:
        items.append({
            'id': d.id,
            'sector_id': d.sector_id,
            'sector': d.sector.nome,
            'data_deposito': d.data_deposito.isoformat() if d.data_deposito else None,
            'valor': str(d.valor),
            'observacao': d.observacao or '',
            'responsavel': d.responsavel.get_full_name() if d.responsavel else ''
        })
    return JsonResponse({'ok': True, 'total': str(total), 'depositos': items})


@login_required
@acesso_restrito(['admin'])
def depositos_detail(request, pk):
    """Retorna um depósito específico em JSON"""
    try:
        d = Deposito.objects.select_related('sector','responsavel').get(pk=pk)
    except Deposito.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Depósito não encontrado'}, status=404)
    return JsonResponse({'ok': True, 'deposito': {
        'id': d.id,
        'sector_id': d.sector_id,
        'sector': d.sector.nome,
        'data_deposito': d.data_deposito.isoformat() if d.data_deposito else None,
        'valor': str(d.valor),
        'observacao': d.observacao or '',
        'responsavel': d.responsavel.get_full_name() if d.responsavel else ''
    }})


@login_required
@require_POST
@acesso_restrito(['admin'])
def depositos_edit(request, pk):
    """
    Edita depósito via POST JSON ou form.
    Campos aceitos: data_deposito, valor, observacao, sector_id
    """
    try:
        dep = Deposito.objects.get(pk=pk)
    except Deposito.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Depósito não encontrado'}, status=404)

    content_type = (request.META.get('CONTENT_TYPE') or request.content_type or '').lower()
    if content_type.startswith('application/json'):
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest('JSON inválido')
        data_deposito = data.get('data_deposito')
        valor = data.get('valor')
        observacao = data.get('observacao', dep.observacao)
        sector_id = data.get('sector_id')
    else:
        data_deposito = request.POST.get('data_deposito')
        valor = request.POST.get('valor')
        observacao = request.POST.get('observacao', dep.observacao)
        sector_id = request.POST.get('sector_id')

    if sector_id:
        try:
            dep.sector = Sector.objects.get(pk=sector_id)
        except Sector.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Sector não encontrado'}, status=404)

    if valor:
        try:
            dep.valor = Decimal(str(valor))
        except Exception:
            return JsonResponse({'ok': False, 'error': 'Valor inválido'}, status=400)
    if data_deposito:
        dep.data_deposito = data_deposito
    dep.observacao = observacao
    dep.responsavel = request.user
    dep.save()
    return JsonResponse({'ok': True, 'deposito_id': dep.id})


@login_required
@require_POST
@acesso_restrito(['admin'])
def depositos_delete(request):
    """
    Excluir depósito via POST JSON {id: pk} ou form (id).
    """
    content_type = (request.META.get('CONTENT_TYPE') or request.content_type or '').lower()
    if content_type.startswith('application/json'):
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest('JSON inválido')
        pk = data.get('id')
    else:
        pk = request.POST.get('id')

    if not pk:
        return JsonResponse({'ok': False, 'error': 'id obrigatório'}, status=400)
    try:
        d = Deposito.objects.get(pk=pk)
        d.delete()
    except Deposito.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Depósito não encontrado'}, status=404)
    return JsonResponse({'ok': True})



# 🔹 Dashboards Especializados
from django.db.models import ExpressionWrapper
@login_required
@acesso_restrito(['admin'])
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


@login_required
@acesso_restrito(['admin'])
def contabilista_financas(request):
    registos = RegistoDiario.objects.annotate(
        saldo_liquido=ExpressionWrapper(
            (F("normal") + F("alunos") + F("luvu") + F("frete")) -
            (F("alimentacao") + F("parqueamento") + F("taxa") + F("outros")),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
    )

    totais = registos.aggregate(
        total_entradas=Sum(F("normal") + F("alunos") + F("luvu") + F("frete"),
                           output_field=DecimalField()),
        total_saidas=Sum(F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"),
                         output_field=DecimalField()),
        total_saldo=Sum("saldo_liquido"),
    )

    # Agregar despesas gerais (Despesas) no sistema
    total_despesas_gerais = Despesa.objects.aggregate(total=Sum('valor', output_field=DecimalField()))['total'] or Decimal('0')

    # Agregar despesas de combustível no sistema (inclui sobragem e lavagem)
    comb_glob = DespesaCombustivel.objects.aggregate(
        total_valor=Sum('valor', output_field=DecimalField()),
        total_sobragem=Sum('sobragem_filtros', output_field=DecimalField()),
        total_lavagem=Sum('lavagem', output_field=DecimalField()),
    )
    total_combustivel_glob = comb_glob.get('total_valor') or Decimal('0')
    total_combustivel_sobragem_glob = comb_glob.get('total_sobragem') or Decimal('0')
    total_combustivel_lavagem_glob = comb_glob.get('total_lavagem') or Decimal('0')

    # Ajustar total de saídas para incluir despesas gerais e combustível (valor + sobragem + lavagem)
    try:
        orig_saidas = Decimal(totais.get('total_saidas') or 0)
    except Exception:
        orig_saidas = Decimal('0')
    totais['total_saidas'] = orig_saidas + total_despesas_gerais + total_combustivel_glob + total_combustivel_sobragem_glob + total_combustivel_lavagem_glob

    # Recalcular saldo global (entradas - saídas ajustadas)
    try:
        totais['total_entradas'] = Decimal(totais.get('total_entradas') or 0)
    except Exception:
        totais['total_entradas'] = Decimal('0')
    totais['total_saldo'] = totais['total_entradas'] - totais['total_saidas']

    despesas = Despesa.objects.all().order_by("-data")[:10]

    return render(request, "dashboards/contabilista_financas.html", {
        "totais": totais,
        "despesas": despesas,
    })


@login_required
def gerencia_financas(request):
    registros = (
        RegistoDiario.objects
        .annotate(
            mes=TruncMonth("data"),
            entradas=ExpressionWrapper(
                F("normal") + F("alunos") + F("luvu") + F("frete"),
                output_field=DecimalField()
            ),
            saidas=ExpressionWrapper(
                F("alimentacao") + F("parqueamento") + F("taxa") + F("outros"),
                output_field=DecimalField()
            ),
        )
        .values("mes")
        .annotate(
            total_entradas=Sum("entradas"),
            total_saidas=Sum("saidas"),
        )
        .order_by("mes")
    )

    labels = [r["mes"].strftime("%b/%Y") if r["mes"] else "N/A" for r in registros]
    lucros = [(r["total_entradas"] or 0) - (r["total_saidas"] or 0) for r in registros]

    custos_mensais = (
        Despesa.objects
        .annotate(mes=TruncMonth("data"))
        .values("mes")
        .annotate(
            salarios=Sum("valor", filter=Q(descricao__icontains="salário")),
            combustivel=Sum("valor", filter=Q(descricao__icontains="combustível")),
            manutencao=Sum("valor", filter=Q(descricao__icontains="manutenção")),
        )
        .order_by("mes")
    )

    custos_labels = [c["mes"].strftime("%b/%Y") if c["mes"] else "N/A" for c in custos_mensais]
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
@acesso_restrito(['admin'])
def gerencia_campo(request):
    # Verificar se o modelo Motorista existe
    try:
        from .models import Motorista
        MOTORISTA_MODEL_EXISTS = True
    except ImportError:
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


# ---------- Cobrador Viagens Views ----------#

@login_required
@acesso_restrito(['admin'])
def cobrador_viagens(request):
    """
    Página com formulário/abas para lançar e ver viagens do cobrador.
    Template: templates/cobradores/cobrador_viagens.html
    """
    # enviar data inicial se quiser
    context = {
        "today": request.GET.get("data") or None
    }
    return render(request, "cobradores/cobrador_viagens.html", context)

@login_required
@require_POST
def cobrador_viagens_save(request):
    """
    Salva uma viagem via POST JSON.
    Espera JSON no body com: autocarro_numero | autocarro_id, data, hora, valor, passageiros, observacao
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("JSON inválido")

    numero = data.get("autocarro_numero") or data.get("autocarro_id")
    if not numero:
        return JsonResponse({"ok": False, "error": "autocarro_numero obrigatório"}, status=400)

    # localizar autocarro (tenta por número, depois por pk)
    try:
        try:
            autocarro = Autocarro.objects.get(numero=numero)
        except Autocarro.DoesNotExist:
            autocarro = Autocarro.objects.get(pk=int(numero))
    except Exception:
        return JsonResponse({"ok": False, "error": "Autocarro não encontrado"}, status=404)

    try:
        valor = Decimal(str(data.get("valor") or "0"))
    except Exception:
        valor = Decimal("0")

    try:
        passageiros = int(data.get("passageiros") or 0)
    except Exception:
        passageiros = 0

    viagem = CobradorViagem.objects.create(
        autocarro=autocarro,
        cobrador=request.user,
        data=data.get("data"),
        hora=data.get("hora") or None,
        valor=valor,
        passageiros=passageiros,
        observacao=data.get("observacao") or ""
    )

    return JsonResponse({"ok": True, "viagem_id": viagem.id})


@login_required
def cobrador_viagens_list(request):
    """
    Retorna JSON com viagens e resumo para um autocarro (por número ou id).
    GET params: autocarro_numero|autocarro_id, opcional data=YYYY-MM-DD
    """
    numero = request.GET.get("autocarro_numero") or request.GET.get("autocarro_id")
    if not numero:
        return JsonResponse({"ok": False, "error": "autocarro_numero obrigatório"}, status=400)

    try:
        try:
            autocarro = Autocarro.objects.get(numero=numero)
        except Autocarro.DoesNotExist:
            autocarro = Autocarro.objects.get(pk=int(numero))
    except Exception:
        return JsonResponse({"ok": False, "error": "Autocarro não encontrado"}, status=404)

    qs = CobradorViagem.objects.filter(autocarro=autocarro)
    data_filtro = request.GET.get("data")
    if data_filtro:
        qs = qs.filter(data=data_filtro)

    viagens = []
    for v in qs.order_by("-data", "-hora"):
        viagens.append({
            "id": v.id,
            "data": v.data.isoformat(),
            "hora": v.hora.isoformat() if v.hora else "",
            "valor": str(v.valor),
            "passageiros": v.passageiros,
            "observacao": v.observacao,
            "cobrador": v.cobrador.get_full_name() if v.cobrador else "",
            "status": getattr(v, "status", "pending"),
        })

    resumo = qs.aggregate(total_valor=Sum("valor"), total_passageiros=Sum("passageiros"))
    total_valor = resumo.get("total_valor") or Decimal("0")
    total_passageiros = resumo.get("total_passageiros") or 0

    return JsonResponse({
        "ok": True,
        "autocarro": {"id": autocarro.id, "numero": autocarro.numero, "modelo": getattr(autocarro, "modelo", "")},
        "viagens": viagens,
        "resumo": {"total_valor": str(total_valor), "total_passageiros": int(total_passageiros)}
    })


@login_required
def cobrador_viagens_validate_list(request):
    """
    Retorna viagens pendentes (ou filtro por autocarro_numero/data).
    Apenas para users com nível 'gestor' ou 'admin'.
    """
    nivel = getattr(request.user, 'nivel_acesso', '').lower()
    if nivel not in ['admin', 'gestor']:
        return JsonResponse({'ok': False, 'error': 'Acesso negado'}, status=403)

    numero = request.GET.get('autocarro_numero') or request.GET.get('autocarro_id')
    data = request.GET.get('data')  # opcional
    qs = CobradorViagem.objects.filter(status='pending')
    if numero:
        try:
            aut = Autocarro.objects.get(numero=numero)
            qs = qs.filter(autocarro=aut)
        except Autocarro.DoesNotExist:
            try:
                qs = qs.filter(autocarro_id=int(numero))
            except Exception:
                return JsonResponse({'ok': False, 'error': 'Autocarro não encontrado'}, status=404)
    if data:
        qs = qs.filter(data=data)
    viagens = []
    for v in qs.order_by('data', 'hora'):
        viagens.append({
            'id': v.id,
            'autocarro_numero': v.autocarro.numero,
            'data': v.data.isoformat(),
            'hora': v.hora.isoformat() if v.hora else '',
            'valor': str(v.valor),
            'passageiros': v.passageiros,
            'observacao': v.observacao,
            'cobrador': v.cobrador.get_full_name() if v.cobrador else '',
            'criado_em': v.criado_em.isoformat(),
        })
    return JsonResponse({'ok': True, 'viagens': viagens})


@login_required
@require_POST
def cobrador_viagens_validate_action(request):
    """
    Ação para aprovar/reprovar via POST JSON:
    { "id": 123, "action": "approve"|"reject", "valor_aprovado": "1000.00", "nota": "..." }
    Apenas 'admin' e 'gestor' podem executar.
    """
    nivel = getattr(request.user, 'nivel_acesso', '').lower()
    if nivel not in ['admin', 'gestor']:
        return JsonResponse({'ok': False, 'error': 'Acesso negado'}, status=403)
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('JSON inválido')
    vid = data.get('id')
    action = data.get('action')
    nota = data.get('nota')
    valor_aprovado = data.get('valor_aprovado', None)
    if not vid or action not in ['approve', 'reject']:
        return JsonResponse({'ok': False, 'error': 'Parâmetros inválidos'}, status=400)
    try:
        viagem = CobradorViagem.objects.get(pk=vid)
    except CobradorViagem.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Viagem não encontrada'}, status=404)

    try:
        if action == 'approve':
            viagem.approve(request.user, valor_aprovado=valor_aprovado, nota=nota)
        else:
            viagem.reject(request.user, nota=nota)
        return JsonResponse({'ok': True, 'status': viagem.status})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ---------- Manutenção Autocarros Views ----------#

@login_required
@acesso_restrito(['admin', 'gestor'])
def manutencao_create(request):
    """
    Página para agendar manutenção.
    Seleciona setor → carrega autocarros do setor → preenche campos e salva.
    """
    if request.method == 'POST':
        form = ManutencaoForm(request.POST, request.FILES)
        if form.is_valid():
            m = form.save(commit=False)
            if not m.responsavel:
                m.responsavel = request.user
            m.save()
            messages.success(request, '✅ Manutenção agendada com sucesso.')
            return redirect('manutencao_list')
        else:
            messages.error(request, '❌ Formulário inválido. Verifique os campos.')
    else:
        form = ManutencaoForm()

    sectores = Sector.objects.all().order_by('nome')
    return render(request, 'autocarros/manutencao_form.html', {'form': form, 'sectores': sectores})


@login_required
def manutencao_list(request):
    qs = Manutencao.objects.select_related('autocarro', 'sector', 'responsavel').all()

    # Tentar ordenar por '-data_ultima' e, se não existir no modelo, usar um fallback para '-data' ou sem ordenação.
    order_field = None
    try:
        Manutencao._meta.get_field('data_ultima')
        order_field = '-data_ultima'
    except Exception:
        try:
            Manutencao._meta.get_field('data')
            order_field = '-data'
        except Exception:
            order_field = None

    if order_field:
        qs = qs.order_by(order_field)

    sector_id = request.GET.get('sector')
    if sector_id:
        qs = qs.filter(sector_id=sector_id)

    return render(request, 'autocarros/manutencao_list.html', {'manutencoes': qs, 'sectores': Sector.objects.all()})


@login_required
@acesso_restrito(['admin', 'gestor'])
def manutencao_edit(request, pk):
    """
    Editar manutenção agendada.
    Apenas admin/gestor podem editar.
    """
    manut = get_object_or_404(Manutencao, pk=pk)
    if request.method == 'POST':
        form = ManutencaoForm(request.POST, request.FILES, instance=manut)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Manutenção atualizada com sucesso.')
            return redirect('manutencao_list')
        else:
            messages.error(request, '❌ Formulário inválido. Verifique os campos.')
    else:
        form = ManutencaoForm(instance=manut)
    return render(request, 'autocarros/manutencao_form.html', {'form': form, 'manut': manut})


@login_required
@acesso_restrito(['admin', 'gestor'])
def manutencao_delete(request, pk):
    """
    Confirmar e eliminar manutenção.
    Apenas admin/gestor podem apagar.
    """
    manut = get_object_or_404(Manutencao, pk=pk)
    if request.method == 'POST':
        manut.delete()
        messages.success(request, '✅ Manutenção eliminada com sucesso.')
        return redirect('manutencao_list')
    return render(request, 'autocarros/confirmar_deletar_manutencao.html', {'manut': manut})


@login_required
def api_autocarros_por_sector(request):
    sector_id = request.GET.get('sector_id')
    if not sector_id:
        return JsonResponse({'ok': False, 'error': 'sector_id obrigatório'}, status=400)
    autos = Autocarro.objects.filter(sector_id=sector_id).values('id','numero','modelo')
    return JsonResponse({'ok': True, 'autocarros': list(autos)})


@login_required
def registro_km_view(request):
    """
    Página: formulário para registar kms por sector + listagem de registros.
    """
    sectores = Sector.objects.all().order_by('nome')
    # listar últimos registros (paginacao simples: últimos 20)
    registros = RegistroKM.objects.select_related('sector').prefetch_related('itens__autocarro').order_by('-data_registo')[:20]

    # preparar dados para listagem com previsão (km_proxima vs km_atual)
    registros_data = []
    for r in registros:
        itens = []
        for it in r.itens.all():
            # buscar manutenção mais recente para o autocarro
            m = Manutencao.objects.filter(autocarro=it.autocarro).order_by('-data_ultima').first()
            km_prox = m.km_proxima if m else None
            falta = None
            status = 'Sem plano'
            if km_prox is not None:
                falta = int(km_prox) - int(it.km_atual)
                if falta <= 0:
                    status = 'Vencida'
                elif falta <= 500:
                    status = 'Próxima'
                else:
                    status = 'OK'
            itens.append({
                'autocarro_numero': it.autocarro.numero,
                'km_atual': it.km_atual,
                'km_prox': km_prox,
                'falta': falta,
                'status': status
            })
        registros_data.append({
            'id': r.id,
            'sector': r.sector.nome,
            'data_registo': r.data_registo.isoformat(),
            'itens': itens
        })

    return render(request, 'autocarros/registro_km.html', {
        'sectores': sectores,
        'registros': registros_data
    })


@login_required
@require_POST
def registro_km_save(request):
    """
    Recebe POST JSON:
    { "sector_id": 1, "data_registo":"YYYY-MM-DD", "itens":[{"autocarro_id":1,"km_atual":12345}, ...] }
    Retorna JSON.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('JSON inválido')

    sector_id = data.get('sector_id')
    itens = data.get('itens', [])
    data_registo = data.get('data_registo', None)
    if not sector_id or not isinstance(itens, list) or not itens:
        return JsonResponse({'ok': False, 'error': 'sector_id e itens obrigatórios'}, status=400)

    try:
        sector = Sector.objects.get(pk=sector_id)
    except Sector.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Sector não encontrado'}, status=404)

    registro = RegistroKM.objects.create(sector=sector, data_registo=data_registo or None)
    created = 0
    for it in itens:
        try:
            aid = int(it.get('autocarro_id'))
            km = int(it.get('km_atual'))
            aut = Autocarro.objects.get(pk=aid, sector=sector)
            RegistroKMItem.objects.create(registro=registro, autocarro=aut, km_atual=km)
            created += 1
        except Exception:
            continue

    return JsonResponse({'ok': True, 'registro_id': registro.id, 'created': created})

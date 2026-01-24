from decimal import Decimal
from datetime import timedelta

from django.shortcuts import render
from django.utils.timezone import now

from ..models import (
    RegistoDiario,
    DespesaCombustivel,
    Sector,
)

# ================================
# FUNÇÃO DE SEMANA (4 COLUNAS)
# ================================
def semana_do_mes_4colunas(data):
    """
    Semana do mês baseada em calendário real:
    - Semana 1 começa no dia 1 até domingo
    - Semanas seguintes: segunda a domingo
    - Se existir 5ª semana, ela é fundida na 4ª
    """
    primeiro_dia = data.replace(day=1)

    # segunda=0, domingo=6
    dias_ate_domingo = 6 - primeiro_dia.weekday()
    fim_primeira_semana = primeiro_dia + timedelta(days=dias_ate_domingo)

    if data <= fim_primeira_semana:
        return 1

    dias_restantes = (data - fim_primeira_semana).days - 1
    semana = 2 + (dias_restantes // 7)

    return min(semana, 4)


# ================================
# VIEW MAPA GERAL FINANCEIRO
# ================================
def mapa_geral_financeiro(request):
    sector_id = request.GET.get("sector")
    mes = int(request.GET.get("mes", now().month))
    ano = int(request.GET.get("ano", now().year))

    sectores = Sector.objects.all()

    if sector_id:
        sector = Sector.objects.get(id=sector_id)
    else:
        sector = sectores.first()

    # ---------------- REGISTOS ----------------
    registos = RegistoDiario.objects.filter(
        autocarro__sector=sector,
        data__year=ano,
        data__month=mes,
        validado=True
    )

    combustiveis = DespesaCombustivel.objects.filter(
        sector=sector,
        data__year=ano,
        data__month=mes
    )

    # ---------------- ESTRUTURA BASE ----------------
    semanas = {
        i: {
            "entradas": {
                "normal": Decimal(0),
                "alunos": Decimal(0),
                "luvu": Decimal(0),
                "frete": Decimal(0),
                "total": Decimal(0),
            },
            "despesas": {
                "alimentacao": Decimal(0),
                "parqueamento": Decimal(0),
                "taxa": Decimal(0),
                "outros": Decimal(0),
                "combustivel": Decimal(0),
                "lavagem": Decimal(0),
                "sopragem": Decimal(0),
                "total": Decimal(0),
            },
            "saldo": Decimal(0),
        }
        for i in range(1, 5)
    }

    # ---------------- REGISTOS DIÁRIOS ----------------
    for r in registos:
        s = semana_do_mes_4colunas(r.data)

        semanas[s]["entradas"]["normal"] += r.normal
        semanas[s]["entradas"]["alunos"] += r.alunos
        semanas[s]["entradas"]["luvu"] += r.luvu
        semanas[s]["entradas"]["frete"] += r.frete

        semanas[s]["despesas"]["alimentacao"] += r.alimentacao
        semanas[s]["despesas"]["parqueamento"] += r.parqueamento
        semanas[s]["despesas"]["taxa"] += r.taxa
        semanas[s]["despesas"]["outros"] += r.outros

    # ---------------- COMBUSTÍVEL / LAVAGEM / SOPRAGEM ----------------
    for d in combustiveis:
        s = semana_do_mes_4colunas(d.data)

        semanas[s]["despesas"]["combustivel"] += d.valor or 0
        semanas[s]["despesas"]["lavagem"] += d.lavagem or 0
        semanas[s]["despesas"]["sopragem"] += d.sobragem_filtros or 0

    # ---------------- TOTAIS E SALDOS ----------------
    total_entradas = Decimal(0)
    total_despesas = Decimal(0)

    for s in semanas.values():
        s["entradas"]["total"] = sum(
            v for k, v in s["entradas"].items() if k != "total"
        )

        s["despesas"]["total"] = sum(
            v for k, v in s["despesas"].items() if k != "total"
        )

        s["saldo"] = s["entradas"]["total"] - s["despesas"]["total"]

        total_entradas += s["entradas"]["total"]
        total_despesas += s["despesas"]["total"]

    context = {
        "sector": sector,
        "sectores": sectores,
        "mes": mes,
        "ano": ano,
        "semanas": semanas,
        "total_entradas": total_entradas,
        "total_despesas": total_despesas,
        "saldo_liquido": total_entradas - total_despesas,
    }

    return render(request, "financeiro/mapa_geral.html", context)

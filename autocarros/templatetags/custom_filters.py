from django import template
from decimal import Decimal, InvalidOperation



register = template.Library()


def _to_decimal(value):
    """Converte value para Decimal de forma tolerante.
    - Trata None, strings vazias e vírgulas.
    - Retorna Decimal('0') se não for possível converter.
    """
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    try:
        s = str(value).strip()
        if s == '':
            return Decimal('0')
        # aceitar vírgula como separador decimal
        s = s.replace(',', '.')
        return Decimal(s)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')

@register.filter
def get_item(dictionary, key):
    """Retorna dictionary[key] ou vazio se não existir"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, {})
    return {}

@register.filter
def add(value, arg):
    """Soma dois valores"""
    a = _to_decimal(value)
    b = _to_decimal(arg)
    return a + b

@register.filter
def soma_campo(registros, campo):
    """Soma um campo específico de uma lista de registros"""
    total = Decimal('0')
    for reg in registros:
        if hasattr(reg, campo):
            valor = getattr(reg, campo)
            if callable(valor):
                total += valor()
            else:
                total += _to_decimal(valor)
    return total

@register.filter
def soma_saldos(registros):
    """Soma total de saldos reais para uma lista de registros"""
    total = Decimal('0')
    for reg in registros:
        total += _to_decimal(getattr(reg, 'saldo_real', Decimal('0')))
    return total

@register.filter
def soma_combustivel_sector(relatorio, despesas_por_autocarro):
    """Soma total de combustível para um relatório de sector"""
    total = Decimal('0')
    sector_despesas = despesas_por_autocarro.get(relatorio.sector.id, {})
    data_despesas = sector_despesas.get(relatorio.data.isoformat(), {})
    
    for autocarro_despesas in data_despesas.values():
        total += autocarro_despesas.get('total_combustivel', Decimal('0'))
    
    return total

@register.filter
def soma_total_autocarros(relatorios):
    """Soma total de autocarros em todos os relatórios"""
    total = 0
    for rel in relatorios:
        total += rel.registos.count()
    return total

# custom_filters.py - ADICIONE ESTES FILTROS NO FINAL DO ARQUIVO

@register.filter
def soma_entradas_validados(registos_validados):
    """Soma total de entradas apenas dos registos validados"""
    total = Decimal('0')
    for reg in registos_validados:
        if hasattr(reg, 'entradas_total') and callable(reg.entradas_total):
            total += _to_decimal(reg.entradas_total() or '0')
        else:
            total += _to_decimal(getattr(reg, 'entradas_total', '0') or '0')
    return total

@register.filter
def soma_saldos_validados(registos_validados):
    """Soma total de saldos líquidos apenas dos registos validados"""
    total = Decimal('0')
    for reg in registos_validados:
        if hasattr(reg, 'saldo_liquido') and callable(reg.saldo_liquido):
            total += _to_decimal(reg.saldo_liquido() or '0')
        else:
            # Tenta calcular se não existir o método
            entradas = Decimal('0')
            saidas = Decimal('0')
            
            if hasattr(reg, 'entradas_total') and callable(reg.entradas_total):
                entradas = _to_decimal(reg.entradas_total() or '0')
            else:
                entradas = _to_decimal(getattr(reg, 'entradas_total', '0') or '0')
                
            if hasattr(reg, 'saidas_total') and callable(reg.saidas_total):
                saidas = _to_decimal(reg.saidas_total() or '0')
            else:
                saidas = _to_decimal(getattr(reg, 'saidas_total', '0') or '0')
            
            total += entradas - saidas
    return total

@register.filter
def soma_campo_validados(registos_validados, campo):
    """Soma um campo específico apenas dos registos validados"""
    total = Decimal('0')
    for reg in registos_validados:
        valor = getattr(reg, campo, '0')
        if callable(valor):
            total += _to_decimal(valor() or '0')
        else:
            total += _to_decimal(valor or '0')
    return total

@register.filter
def subtract(value, arg):
    """Subtrai dois valores"""
    try:
        return int(value) - int(arg)
    except (TypeError, ValueError):
        a = _to_decimal(value)
        b = _to_decimal(arg)
        return a - b

@register.filter
def filter_validados(registos):
    """Filtra apenas os registos que estão validados"""
    if hasattr(registos, 'filter'):
        # Se for um QuerySet
        return registos.filter(validado=True)
    else:
        # Se for uma lista Python
        return [reg for reg in registos if getattr(reg, 'validado', False)]

@register.filter
def filter_concluidos(registos):
    """Filtra apenas os registos que estão concluídos"""
    if hasattr(registos, 'filter'):
        return registos.filter(concluido=True)
    else:
        return [reg for reg in registos if getattr(reg, 'concluido', False)]

@register.filter
def count_validados(registos):
    """Conta quantos registos estão validados"""
    if hasattr(registos, 'filter'):
        return registos.filter(validado=True).count()
    else:
        return len([reg for reg in registos if getattr(reg, 'validado', False)])

@register.filter
def count_concluidos(registos):
    """Conta quantos registos estão concluídos"""
    if hasattr(registos, 'filter'):
        return registos.filter(concluido=True).count()
    else:
        return len([reg for reg in registos if getattr(reg, 'concluido', False)])
    
from django import template
register = template.Library()

@register.filter(name='add_class')
def add_class(field, css):
    return field.as_widget(attrs={"class": css})

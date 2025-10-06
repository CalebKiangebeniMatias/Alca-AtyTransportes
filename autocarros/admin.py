from django.contrib import admin
from .models import (
    Autocarro, CustomUser, EstadoAutocarro, Sector, RelatorioSector, 
    RegistoDiario, Despesa, DespesaCombustivel, 
    Comprovativo, RegistoArquivo, Motorista, ComprovativoRelatorio
)
from django.contrib import admin
from .models import Sector


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ("nome", "gestor")
    search_fields = ("nome", "gestor__username", "gestor__email")
    list_filter = ("gestor",)
    autocomplete_fields = ["gestor"]


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    search_fields = ("username", "email", "first_name", "last_name")
    list_display = ("username", "email", "nivel_acesso", "is_active")


@admin.register(RelatorioSector)
class RelatorioSectorAdmin(admin.ModelAdmin):
    list_display = ['sector', 'data', 'descricao_curta', 'quantidade_comprovativos', 'quantidade_registros']
    list_filter = ['sector', 'data']
    search_fields = ['sector__nome', 'descricao']
    date_hierarchy = 'data'
    
    def descricao_curta(self, obj):
        """Retorna uma descrição curta para a listagem"""
        if obj.descricao:
            return obj.descricao[:50] + '...' if len(obj.descricao) > 50 else obj.descricao
        return '-'
    descricao_curta.short_description = 'Descrição'
    
    def quantidade_comprovativos(self, obj):
        """Retorna a quantidade de comprovativos do relatório"""
        return obj.comprovativos.count()
    quantidade_comprovativos.short_description = 'Comprovativos'
    
    def quantidade_registros(self, obj):
        """Retorna a quantidade de registros do relatório"""
        return obj.registos.count()
    quantidade_registros.short_description = 'Registros'


@admin.register(ComprovativoRelatorio)
class ComprovativoRelatorioAdmin(admin.ModelAdmin):
    list_display = ['relatorio', 'arquivo', 'descricao_curta', 'enviado_em']
    list_filter = ['relatorio__sector', 'enviado_em']
    search_fields = ['relatorio__sector__nome', 'descricao']
    date_hierarchy = 'enviado_em'
    
    def descricao_curta(self, obj):
        """Retorna uma descrição curta para a listagem"""
        if obj.descricao:
            return obj.descricao[:30] + '...' if len(obj.descricao) > 30 else obj.descricao
        return '-'
    descricao_curta.short_description = 'Descrição'


@admin.register(Autocarro)
class AutocarroAdmin(admin.ModelAdmin):
    list_display = ['numero', 'modelo', 'placa', 'sector', 'status']
    list_filter = ['sector', 'status']
    search_fields = ['numero', 'modelo', 'placa']
    list_editable = ['status']


@admin.register(EstadoAutocarro)
class EstadoAutocarroAdmin(admin.ModelAdmin):
    list_display = ['autocarro', 'data', 'motor_funciona', 'pneus_bons', 'luzes_funcionam']
    list_filter = ['autocarro__sector', 'data']
    search_fields = ['autocarro__numero']
    date_hierarchy = 'data'


class RegistoDiarioAdmin(admin.ModelAdmin):
    # 🔹 CORRIGIR list_display - remover 'relatorio'
    list_display = [
        'autocarro', 
        'data', 
        'entradas_total', 
        'saidas_total', 
        'saldo_liquido',
        'concluido',
        'validado'
    ]
    
    # 🔹 CORRIGIR list_filter - usar campos existentes
    list_filter = [
        'autocarro__sector',  # Agora está correto - sector via autocarro
        'data',
        'concluido',
        'validado'
    ]
    
    # 🔹 ADICIONAR search_fields
    search_fields = [
        'autocarro__numero',
        'motorista',
        'cobrador_principal'
    ]
    
    # 🔹 ADICIONAR list_editable para status
    list_editable = ['concluido', 'validado']
    
    # 🔹 ADICIONAR date_hierarchy
    date_hierarchy = 'data'

admin.site.register(RegistoDiario, RegistoDiarioAdmin)


@admin.register(Despesa)
class DespesaAdmin(admin.ModelAdmin):
    list_display = ['descricao_curta', 'valor', 'data', 'numero_transacao']
    list_filter = ['data']
    search_fields = ['descricao', 'numero_transacao']
    date_hierarchy = 'data'
    
    def descricao_curta(self, obj):
        return obj.descricao[:50] + '...' if len(obj.descricao) > 50 else obj.descricao
    descricao_curta.short_description = 'Descrição'


@admin.register(DespesaCombustivel)
class DespesaCombustivelAdmin(admin.ModelAdmin):
    list_display = ['autocarro', 'sector', 'data', 'valor', 'litros_calculados']
    list_filter = ['sector', 'data', 'autocarro']
    search_fields = ['autocarro__numero', 'descricao']
    date_hierarchy = 'data'
    
    def litros_calculados(self, obj):
        return f"{obj.litros:.2f} L" if obj.litros > 0 else '-'
    litros_calculados.short_description = 'Litros'


@admin.register(Comprovativo)
class ComprovativoAdmin(admin.ModelAdmin):
    list_display = ['despesa', 'arquivo', 'enviado_em']
    list_filter = ['enviado_em']
    search_fields = ['despesa__descricao']
    date_hierarchy = 'enviado_em'


@admin.register(RegistoArquivo)
class RegistoArquivoAdmin(admin.ModelAdmin):
    list_display = ['registo', 'arquivo', 'descricao_curta']
    list_filter = ['registo__autocarro__sector']
    search_fields = ['registo__autocarro__numero', 'descricao']
    
    def descricao_curta(self, obj):
        if obj.descricao:
            return obj.descricao[:30] + '...' if len(obj.descricao) > 30 else obj.descricao
        return '-'
    descricao_curta.short_description = 'Descrição'


@admin.register(Motorista)
class MotoristaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'telefone', 'ativo']
    list_filter = ['ativo']
    search_fields = ['nome', 'telefone', 'numero_bi']
    list_editable = ['ativo']


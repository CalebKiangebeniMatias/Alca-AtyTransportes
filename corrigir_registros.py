import os
import django
import sys

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_autocarros.settings')
django.setup()

from autocarros.models import RegistoDiario, RelatorioSector, Autocarro
from django.utils import timezone

def corrigir_registros_quebrados():
    """Corrige registros que não têm relatorio associado"""
    print("🔧 Procurando registros quebrados...")
    
    # Encontrar registros sem relatório
    registros_quebrados = RegistoDiario.objects.filter(relatorio__isnull=True)
    print(f"📊 Encontrados {registros_quebrados.count()} registros sem relatório")
    
    for registro in registros_quebrados:
        print(f"🔧 Processando registro {registro.pk}...")
        
        # Tentar encontrar relatório compatível
        relatorio_compativel = RelatorioSector.objects.filter(
            sector=registro.autocarro.sector,
            data=registro.data
        ).first()
        
        if relatorio_compativel:
            registro.relatorio = relatorio_compativel
            registro.save()
            print(f"✅ Registro {registro.pk} associado ao relatório {relatorio_compativel.pk}")
        else:
            # Criar novo relatório
            novo_relatorio = RelatorioSector.objects.create(
                sector=registro.autocarro.sector,
                data=registro.data,
                descricao="Relatório criado automaticamente para correção"
            )
            registro.relatorio = novo_relatorio
            registro.save()
            print(f"✅ Criado relatório {novo_relatorio.pk} para registro {registro.pk}")
    
    # Verificar se ainda existem problemas
    registros_restantes = RegistoDiario.objects.filter(relatorio__isnull=True).count()
    print(f"📊 Registros restantes sem relatório: {registros_restantes}")
    
    if registros_restantes == 0:
        print("🎉 Todos os registros foram corrigidos com sucesso!")
    else:
        print("⚠️  Ainda existem registros problemáticos.")

if __name__ == "__main__":
    corrigir_registros_quebrados()

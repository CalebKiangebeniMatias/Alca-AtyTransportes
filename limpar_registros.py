# limpar_registros.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_autocarros.settings')
django.setup()

from autocarros.models import RegistoDiario
from django.db.models import Count

def limpar_registros_duplicados():
    print("🔄 Iniciando limpeza de registros duplicados...")
    
    # Encontrar duplicados
    duplicados = RegistoDiario.objects.values('autocarro', 'data').annotate(
        total=Count('id')
    ).filter(total__gt=1)
    
    print(f"📊 Encontrados {len(duplicados)} grupos de registros duplicados")
    
    total_excluidos = 0
    
    for dup in duplicados:
        registros = RegistoDiario.objects.filter(
            autocarro_id=dup['autocarro'], 
            data=dup['data']
        ).order_by('-id')
        
        # Manter o mais recente, excluir os outros
        if registros.count() > 1:
            registro_manter = registros.first()
            excluir_count = registros.exclude(id=registro_manter.id).count()
            registros.exclude(id=registro_manter.id).delete()
            total_excluidos += excluir_count
            print(f"✅ Autocarro {dup['autocarro']}, Data {dup['data']}: {excluir_count} excluídos")
    
    print(f"\n🎯 Limpeza concluída!")
    print(f"📝 Registros excluídos: {total_excluidos}")
    print(f"💾 Registros restantes: {RegistoDiario.objects.count()}")

if __name__ == "__main__":
    limpar_registros_duplicados()

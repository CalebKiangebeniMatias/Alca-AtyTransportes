# testar_sistema.py
import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_autocarros.settings')
django.setup()

from autocarros.models import RegistoDiario, Autocarro, Sector

def testar_sistema():
    print("🧪 TESTANDO O SISTEMA")
    
    # 1. Verificar se há sectores e autocarros
    sectores = Sector.objects.all()
    autocarros = Autocarro.objects.all()
    
    print(f"📋 Sectores: {sectores.count()}")
    print(f"🚌 Autocarros: {autocarros.count()}")
    
    if autocarros.count() == 0:
        print("❌ Nenhum autocarro cadastrado. Cadastre autocarros primeiro.")
        return
    
    # 2. Testar criação de registros
    print("\n🔧 TESTANDO CRIAÇÃO DE REGISTROS:")
    
    autocarro_teste = autocarros.first()
    data_teste = date.today()
    
    try:
        # Primeiro registro (deve funcionar)
        registro1 = RegistoDiario.objects.create(
            autocarro=autocarro_teste,
            data=data_teste,
            normal=100.00,
            numero_passageiros=50
        )
        print("✅ Primeiro registro criado com sucesso!")
        
        # Tentar criar segundo registro (deve falhar)
        try:
            registro2 = RegistoDiario.objects.create(
                autocarro=autocarro_teste,
                data=data_teste,
                normal=200.00
            )
            print("❌ ERRO: Segundo registro foi criado (deveria falhar)")
        except Exception as e:
            print("✅ CORRETO: Segundo registro bloqueado pela constraint")
            
        # Criar registro para data diferente (deve funcionar)
        registro3 = RegistoDiario.objects.create(
            autocarro=autocarro_teste,
            data=date(2025, 9, 27),  # Data diferente
            normal=150.00
        )
        print("✅ Registro com data diferente criado com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
    
    # 3. Estatísticas finais
    print(f"\n📊 ESTATÍSTICAS FINAIS:")
    print(f"Total de registros: {RegistoDiario.objects.count()}")
    
    # Verificar duplicados
    from django.db.models import Count
    duplicados = RegistoDiario.objects.values('autocarro', 'data').annotate(
        total=Count('id')
    ).filter(total__gt=1)
    
    print(f"Registros duplicados: {len(duplicados)}")

if __name__ == "__main__":
    testar_sistema()

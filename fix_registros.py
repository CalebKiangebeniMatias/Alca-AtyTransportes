import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_autocarros.settings')
django.setup()

from autocarros.models import RegistoDiario, RelatorioSector

def fix_registros_sem_relatorio():
    """Corrige registros que não têm relatorio associado"""
    registros_quebrados = RegistoDiario.objects.filter(relatorio__isnull=True)
    
    print(f"Encontrados {registros_quebrados.count()} registros sem relatório")
    
    for registro in registros_quebrados:
        # Tentar encontrar um relatório compatível pela data e setor
        relatorio_compativel = RelatorioSector.objects.filter(
            sector=registro.autocarro.sector,
            data=registro.data
        ).first()
        
        if relatorio_compativel:
            registro.relatorio = relatorio_compativel
            registro.save()
            print(f"✅ Corrigido: Registro {registro.pk} associado ao relatório {relatorio_compativel.pk}")
        else:
            # Criar um novo relatório se não existir
            novo_relatorio = RelatorioSector.objects.create(
                sector=registro.autocarro.sector,
                data=registro.data,
                descricao=f"Relatório criado automaticamente para corrigir registro {registro.pk}"
            )
            registro.relatorio = novo_relatorio
            registro.save()
            print(f"✅ Criado novo relatório {novo_relatorio.pk} para registro {registro.pk}")

if __name__ == "__main__":
    fix_registros_sem_relatorio()

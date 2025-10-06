from autocarros.models import Despesa, Comprovativo, Sector
from django.core.files import File
from django.utils import timezone
import os

# Cria um sector de teste (se não existir)
sector, created = Sector.objects.get_or_create(nome='Teste-automatizado', defaults={'slug': 'teste-automatizado'})

# Criar a despesa
data = timezone.now().date()
despesa = Despesa.objects.create(
    descricao='Despesa de teste criada por script',
    valor='123.45',
    data=data,
    numero_transacao='TX-001',
    numero_requisicao='RQ-001',
    sector=sector
)

# Criar arquivos de teste no diretório atual
files = []
for i, content in enumerate([b"conteudo teste 1", b"conteudo teste 2"], start=1):
    fname = f"test_comprovativo_{i}.txt"
    with open(fname, 'wb') as f:
        f.write(content)
    files.append(fname)

# Anexar comprovativos
for fname in files:
    f = open(fname, 'rb')
    try:
        Comprovativo.objects.create(despesa=despesa, arquivo=File(f, name=os.path.basename(fname)))
    finally:
        f.close()

# Verificar
count = despesa.comprovativos.count()
print('Despesa criada id=', despesa.id, 'comprovativos=', count)

# Limpar arquivos locais de teste
for fname in files:
    try:
        os.remove(fname)
    except Exception:
        pass

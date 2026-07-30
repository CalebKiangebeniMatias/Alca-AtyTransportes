import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autocarros', '0015_registodiario_taxi_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Peca',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150)),
                ('referencia', models.CharField(blank=True, help_text='Código / referência da peça (opcional)', max_length=100)),
                ('categoria', models.CharField(blank=True, help_text='Ex: Elétrica, Motor, Suspensão, Freios...', max_length=100)),
                ('fornecedor', models.CharField(blank=True, max_length=150)),
                ('unidade_medida', models.CharField(choices=[('un', 'Unidade'), ('par', 'Par'), ('kg', 'Quilograma'), ('l', 'Litro'), ('m', 'Metro'), ('cx', 'Caixa')], default='un', max_length=5)),
                ('preco_unitario', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('quantidade_estoque', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('observacao', models.TextField(blank=True, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Peça',
                'verbose_name_plural': 'Peças',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='Movimentacao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('entrada', 'Entrada'), ('saida', 'Saída')], max_length=10)),
                ('quantidade', models.DecimalField(decimal_places=2, max_digits=12)),
                ('data', models.DateField()),
                ('observacao', models.TextField(blank=True, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('autocarro', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimentacoes_peca', to='autocarros.autocarro')),
                ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimentacoes_peca', to=settings.AUTH_USER_MODEL)),
                ('sector', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimentacoes_peca', to='autocarros.sector')),
                ('peca', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movimentacoes', to='autocarros.peca')),
            ],
            options={
                'verbose_name': 'Movimentação de Peça',
                'verbose_name_plural': 'Movimentações de Peças',
                'ordering': ['-data', '-criado_em'],
            },
        ),
    ]

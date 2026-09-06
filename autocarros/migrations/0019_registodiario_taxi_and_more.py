import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autocarros', '0018_registodiario_taxi_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Caixa',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField(help_text='Data do lançamento (normalmente hoje)')),
                ('valor_saida_combustivel', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Valor gasto em combustível neste autocarro, neste dia', max_digits=14)),
                ('observacao', models.TextField(blank=True, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('autocarro', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='caixas', to='autocarros.autocarro')),
                ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='caixas', to=settings.AUTH_USER_MODEL)),
                ('sector', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='caixas', to='autocarros.sector')),
            ],
            options={
                'verbose_name': 'Registo de Caixa',
                'verbose_name_plural': 'Registos de Caixa',
                'ordering': ['-data', '-criado_em'],
            },
        ),
    ]
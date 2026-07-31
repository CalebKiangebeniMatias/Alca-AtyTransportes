import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autocarros', '0016_peca_registodiario_taxi_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Bateria',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fornecedor', models.CharField(help_text='Nome do fornecedor da bateria', max_length=150)),
                ('marca', models.CharField(help_text='Marca da bateria (ex: Bosch, Varta...)', max_length=100)),
                ('referencia', models.CharField(help_text='Referência / código do modelo da bateria', max_length=100)),
                ('data_compra', models.DateField(help_text='Data em que a bateria foi comprada')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Bateria',
                'verbose_name_plural': 'Baterias',
                'ordering': ['-data_compra', '-criado_em'],
            },
        ),
        migrations.CreateModel(
            name='TrocaBateria',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('local', models.CharField(choices=[('principal', 'Principal'), ('auxiliar', 'Auxiliar')], help_text='Posição da bateria no autocarro', max_length=20)),
                ('data_troca', models.DateField(help_text='Data em que a troca foi realizada')),
                ('km_troca', models.DecimalField(blank=True, decimal_places=2, help_text='Km do autocarro no momento da troca (opcional, usado para prever a próxima troca)', max_digits=14, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('autocarro', models.ForeignKey(help_text='Autocarro onde a bateria foi instalada', on_delete=django.db.models.deletion.CASCADE, related_name='trocas_bateria', to='autocarros.autocarro')),
                ('bateria', models.ForeignKey(help_text='Bateria que foi instalada nesta troca', on_delete=django.db.models.deletion.CASCADE, related_name='trocas', to='autocarros.bateria')),
            ],
            options={
                'verbose_name': 'Troca de Bateria',
                'verbose_name_plural': 'Trocas de Baterias',
                'ordering': ['-data_troca', '-criado_em'],
            },
        ),
    ]
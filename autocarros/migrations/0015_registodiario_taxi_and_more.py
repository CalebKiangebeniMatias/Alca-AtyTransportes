import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autocarros', '0014_pneu_registodiario_taxi_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Troca',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('local', models.CharField(choices=[('dianteira_e', 'Dianteira-E'), ('dianteira_d', 'Dianteira-D'), ('traseira_e_0', 'Traseira-E-0'), ('traseira_e_1', 'Traseira-E-1'), ('traseira_d_0', 'Traseira-D-0'), ('traseira_d_1', 'Traseira-D-1')], help_text='Posição do pneu no autocarro', max_length=20)),
                ('data_troca', models.DateField(help_text='Data em que a troca foi realizada')),
                ('km_troca', models.DecimalField(blank=True, decimal_places=2, help_text='Km do autocarro no momento da troca (opcional, usado para prever a próxima troca)', max_digits=14, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('autocarro', models.ForeignKey(help_text='Autocarro onde o pneu foi instalado', on_delete=django.db.models.deletion.CASCADE, related_name='trocas_pneu', to='autocarros.autocarro')),
                ('pneu', models.ForeignKey(help_text='Pneu que foi instalado nesta troca', on_delete=django.db.models.deletion.CASCADE, related_name='trocas', to='autocarros.pneu')),
            ],
            options={
                'verbose_name': 'Troca de Pneu',
                'verbose_name_plural': 'Trocas de Pneus',
                'ordering': ['-data_troca', '-criado_em'],
            },
        ),
    ]
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autocarros', '0013_registodiario_taxi_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pneu',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fornecedor', models.CharField(help_text='Nome do fornecedor do pneu', max_length=150)),
                ('marca', models.CharField(help_text='Marca do pneu (ex: Michelin, Bridgestone...)', max_length=100)),
                ('referencia', models.CharField(help_text='Referência / código do modelo do pneu', max_length=100)),
                ('data_compra', models.DateField(help_text='Data em que o pneu foi comprado')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Pneu',
                'verbose_name_plural': 'Pneus',
                'ordering': ['-data_compra', '-criado_em'],
            },
        ),
        migrations.AddField(
            model_name='registodiario',
            name='taxi',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='relatoriosector',
            name='alimentacao_estaleiro',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Despesa com alimentação do estaleiro'),
        ),
    ]
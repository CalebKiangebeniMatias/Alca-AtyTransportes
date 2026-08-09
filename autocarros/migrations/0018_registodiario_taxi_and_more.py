import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autocarros', '0017_bateria_registodiario_taxi_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MovimentoBancario',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField()),
                ('tipo', models.CharField(choices=[('debito', 'Débito'), ('credito', 'Crédito')], max_length=10)),
                ('valor', models.DecimalField(decimal_places=2, max_digits=14)),
                ('observacao', models.TextField(blank=True, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('autocarro', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimentos_bancarios', to='autocarros.autocarro', verbose_name='Auxiliar')),
                ('pgc', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movimentos_bancarios', to='autocarros.planocontas', verbose_name='Plano de Contas')),
                ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimentos_bancarios', to=settings.AUTH_USER_MODEL)),
                ('sector', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimentos_bancarios', to='autocarros.sector')),
            ],
            options={
                'verbose_name': 'Movimento Bancário',
                'verbose_name_plural': 'Movimentos Bancários',
                'ordering': ['-data', '-criado_em'],
            },
        ),
    ]
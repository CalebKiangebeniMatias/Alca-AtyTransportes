import json
import os
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from autocarros.models import PlanoContas


class Command(BaseCommand):
    help = (
        "Carrega o plano de contas base (fixtures/plano_base.json) para a "
        "tabela PlanoContas. Pensado para correr via shell (Render Shell / "
        "SSH), evitando o timeout do worker HTTP quando há muitas contas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Apaga as contas existentes antes de importar (CUIDADO: destrutivo).",
        )
        parser.add_argument(
            "--caminho",
            default=None,
            help="Caminho alternativo para o ficheiro JSON do plano base.",
        )

    def handle(self, *args, **options):
        inicio = time.monotonic()

        caminho = options["caminho"] or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "fixtures",
            "plano_base.json",
        )

        if not os.path.exists(caminho):
            raise CommandError(f"Ficheiro não encontrado: {caminho}")

        if PlanoContas.objects.exists():
            if not options["force"]:
                raise CommandError(
                    "Já existem contas registadas. Usa --force para apagar "
                    "e reimportar, ou limpa a tabela manualmente primeiro."
                )
            self.stdout.write(self.style.WARNING("A apagar contas existentes..."))
            PlanoContas.objects.all().delete()

        with open(caminho, encoding="utf-8") as ficheiro:
            dados = json.load(ficheiro)

        self.stdout.write(f"A importar {len(dados)} conta(s) de '{caminho}'...")

        mapa = {}
        criadas = 0
        with transaction.atomic():
            for i, item in enumerate(dados, start=1):
                mae = mapa.get(item.get("parent_codigo"))
                conta = PlanoContas.objects.create(
                    codigo=item["codigo"],
                    nome=item["nome"],
                    tipo=item["tipo"],
                    natureza=item["natureza"],
                    parent=mae,
                )
                mapa[item["codigo"]] = conta
                criadas += 1

                if criadas % 50 == 0 or criadas == len(dados):
                    self.stdout.write(f"  ... {criadas}/{len(dados)} contas processadas")

        duracao = time.monotonic() - inicio
        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído: {criadas} conta(s) importada(s) em {duracao:.1f}s."
            )
        )
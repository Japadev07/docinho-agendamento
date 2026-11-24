"""Carga inicial: cria contratantes, recreadores e festas de demonstração.

Uso (na pasta do projeto):
    python scripts/carga_inicial.py                 # cria dados/docinho.json se não existir
    python scripts/carga_inicial.py --forcar        # recria o arquivo do zero
    python scripts/carga_inicial.py --dados outro.json

O script usa os mesmos serviços do sistema, então todas as regras de negócio
(avisos, escala, brinde da primeira contratação) valem também para a carga.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from docinho import Sistema  # noqa: E402
from docinho.excecoes import DocinhoErro  # noqa: E402


def carregar(sistema: Sistema, definicao: dict, hoje: date) -> None:
    ids_recreadores = {}
    for nome in definicao["recreadores"]:
        recreador = sistema.recreadores.cadastrar(nome)
        ids_recreadores[nome] = recreador.id

    ids_contratantes = {}
    for item in definicao["contratantes"]:
        contratante = sistema.contratantes.cadastrar(item["nome"], item["telefone"])
        ids_contratantes[item["nome"]] = contratante.id

    for item in definicao["festas"]:
        festa = sistema.festas.agendar(
            contratante_id=ids_contratantes[item["contratante"]],
            data=hoje + timedelta(days=item["dias_a_partir_de_hoje"]),
            inicio=item["inicio"],
            termino=item["termino"],
            endereco=item["endereco"],
            quantidade_criancas=item["quantidade_criancas"],
            faixa_etaria=tuple(item["faixa_etaria"]),
            valor_combinado=item["valor_combinado"],
            atividades=item["atividades"],
            recreadores_ids=[ids_recreadores[nome] for nome in item["recreadores"]],
            brinde=item["brinde"],
            deslocamento=item["deslocamento"],
            data_confirmacao=hoje,
        )
        for valor in item["pagamentos"]:
            sistema.financeiro.registrar_pagamento(festa.id, valor, hoje)
        print(f"  {festa}")


def principal() -> int:
    analisador = argparse.ArgumentParser(description="Carga inicial do sistema Docinho.")
    analisador.add_argument("--dados", default=str(RAIZ / "dados" / "docinho.json"))
    analisador.add_argument("--origem", default=str(RAIZ / "dados" / "dados_iniciais.json"))
    analisador.add_argument("--forcar", action="store_true", help="apaga e recria o arquivo de dados")
    argumentos = analisador.parse_args()

    destino = Path(argumentos.dados)
    if destino.exists():
        if not argumentos.forcar:
            print(f"'{destino}' já existe. Use --forcar para recriar do zero.")
            return 1
        destino.unlink()

    with open(argumentos.origem, "r", encoding="utf-8") as arquivo:
        definicao = json.load(arquivo)

    try:
        print(f"Criando {destino} ...")
        carregar(Sistema.com_arquivo(destino), definicao, date.today())
    except DocinhoErro as erro:
        print(f"Erro na carga inicial: {erro}")
        return 1
    print("Carga inicial concluída.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())

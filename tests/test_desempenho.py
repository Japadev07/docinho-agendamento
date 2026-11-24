"""RNF-06 (proposta do PRD): agenda e busca em até 3 segundos em 95% de
20 consultas com 100 eventos."""

import time
from datetime import timedelta

from conftest import HOJE
from docinho import Sistema


def test_rnf06_agenda_e_busca_com_100_eventos():
    sistema = Sistema()
    ana = sistema.recreadores.cadastrar("Ana Lima")
    contratantes = [
        sistema.contratantes.cadastrar(f"Contratante {i:03d}", f"(99) 98{i:03d}-{i:04d}"[:15])
        for i in range(10)
    ]
    for i in range(100):
        sistema.festas.agendar(
            contratante_id=contratantes[i % 10].id,
            data=HOJE + timedelta(days=i + 1),
            inicio="14:00",
            termino="17:00",
            endereco=f"Rua {i}, {i}",
            quantidade_criancas=8,
            faixa_etaria=(4, 9),
            valor_combinado="1000.00",
            atividades=["Pintura facial"],
            recreadores_ids=[ana.id],
            brinde="não se aplica",
            deslocamento="não se aplica",
            data_confirmacao=HOJE,
        )
    assert len(sistema.agenda.consultar()) == 100

    duracoes = []
    for i in range(20):
        inicio = time.perf_counter()
        if i % 2 == 0:
            sistema.agenda.consultar(data_inicial=HOJE + timedelta(days=i), data_final=HOJE + timedelta(days=i + 30))
        else:
            sistema.contratantes.buscar(f"contratante 00{i % 10}")
        duracoes.append(time.perf_counter() - inicio)

    dentro_do_limite = sum(1 for d in duracoes if d <= 3.0)
    assert dentro_do_limite / len(duracoes) >= 0.95

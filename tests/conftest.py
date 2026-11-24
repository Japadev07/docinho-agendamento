"""Fixtures compartilhadas pelos testes."""

from datetime import date

import pytest

from docinho import Sistema
from docinho.excecoes import PersistenciaErro
from docinho.persistencia import RepositorioMemoria

HOJE = date(2026, 11, 24)  # data de confirmação usada nos cenários
DATA_FESTA = date(2026, 12, 20)  # 26 dias depois de HOJE

NOMES_RECREADORES = ["Ana Lima", "Bruno Costa", "Camila Rocha", "Diego Alves", "Elisa Prado", "Felipe Nunes"]


class RepositorioFalho(RepositorioMemoria):
    """Repositório que simula falha de gravação (RNF-03)."""

    def __init__(self):
        super().__init__()
        self.falhar = False

    def salvar(self, dados):
        if self.falhar:
            raise PersistenciaErro("disco cheio (simulado)")
        super().salvar(dados)


@pytest.fixture
def sistema():
    return Sistema()  # persistência em memória


@pytest.fixture
def contratante(sistema):
    return sistema.contratantes.cadastrar("Maria Souza", "(99) 98123-4567")


@pytest.fixture
def recreadores(sistema):
    return [sistema.recreadores.cadastrar(nome) for nome in NOMES_RECREADORES]


@pytest.fixture
def dados_festa(contratante, recreadores):
    """Dados completos e válidos para agendar uma festa."""
    return dict(
        contratante_id=contratante.id,
        data=DATA_FESTA,
        inicio="14:00",
        termino="17:00",
        endereco="Rua das Flores, 120 — Balsas-MA",
        quantidade_criancas=8,
        faixa_etaria=(4, 9),
        valor_combinado="1000.00",
        atividades=["Pintura facial", "Caça ao tesouro"],
        recreadores_ids=[recreadores[0].id, recreadores[1].id],
        brinde="não se aplica",
        deslocamento="não se aplica",
        data_confirmacao=HOJE,
    )


@pytest.fixture
def festa(sistema, dados_festa):
    return sistema.festas.agendar(**dados_festa)


@pytest.fixture
def agendar(sistema, dados_festa):
    """Agenda uma festa a partir dos dados-base com alterações pontuais."""

    def _agendar(**mudancas):
        return sistema.festas.agendar(**{**dados_festa, **mudancas})

    return _agendar


@pytest.fixture
def outro_contratante(sistema):
    return sistema.contratantes.cadastrar("João Pereira", "(99) 99876-5432")

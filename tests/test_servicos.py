"""Testes dos serviços e das regras de negócio (cenários CT-01 a CT-10 da SRS)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from conftest import DATA_FESTA, HOJE
from docinho import Sistema
from docinho.excecoes import (
    CampoObrigatorioErro,
    ConflitoEscalaErro,
    NaoEncontradoErro,
    RegraDeNegocioErro,
    TransicaoInvalidaErro,
    ValidacaoErro,
)
from docinho.modelos import (
    BRINDE_PRIMEIRA_CONTRATACAO,
    Atividade,
    FaixaEtaria,
    SituacaoFesta,
    SituacaoLembrete,
    TipoConflito,
    TipoLembrete,
)
from docinho.servicos import (
    HORARIO_PREFERIDO_ENVIO,
    INTERVALO_MINIMO,
    Agenda,
    AvisoConfirmacao,
    ServicoLembrete,
    RegraDeAviso,
)


def tipos(festa, situacao=None):
    return [l.tipo for l in festa.lembretes if situacao is None or l.situacao is situacao]


def datas_por_tipo(festa):
    return {l.tipo: l.data_prevista for l in festa.lembretes if l.pendente}


# ==========================================================================
# CT-01 / RF-01 — Contratantes
# ==========================================================================
class TesteServicoContratante:
    def test_ct01_cadastrar_e_localizar_por_nome_e_telefone(self, sistema):
        maria = sistema.contratantes.cadastrar("Maria Souza", "(99) 98123-4567")
        sistema.contratantes.cadastrar("João Pereira", "(99) 99876-5432")

        assert sistema.contratantes.buscar("maria") == [maria]
        assert sistema.contratantes.buscar("SOUZA") == [maria]
        assert sistema.contratantes.buscar("joao")[0].nome == "João Pereira"  # sem acento
        assert sistema.contratantes.buscar("(99) 98123-4567") == [maria]
        assert sistema.contratantes.buscar("981234567") == [maria]
        assert sistema.contratantes.buscar("99981234567") == [maria]
        assert sistema.contratantes.buscar("inexistente") == []

    def test_busca_sem_termo_e_recusada(self, sistema):
        with pytest.raises(ValidacaoErro):
            sistema.contratantes.buscar("   ")

    def test_cadastro_recusa_dados_invalidos_e_telefone_repetido(self, sistema):
        sistema.contratantes.cadastrar("Maria Souza", "(99) 98123-4567")
        with pytest.raises(RegraDeNegocioErro, match="mesmo telefone|este telefone"):
            sistema.contratantes.cadastrar("Outra Maria", "99981234567")
        with pytest.raises(ValidacaoErro):
            sistema.contratantes.cadastrar("", "99981234567")
        with pytest.raises(ValidacaoErro):
            sistema.contratantes.cadastrar("Ana", "123")
        assert len(sistema.contratantes.listar()) == 1

    def test_atualizar(self, sistema, contratante, outro_contratante):
        sistema.contratantes.atualizar(contratante.id, nome="Maria S. Souza")
        assert sistema.contratantes.obter(contratante.id).nome == "Maria S. Souza"
        sistema.contratantes.atualizar(contratante.id, telefone="(99) 97777-0000")
        assert sistema.contratantes.buscar("97777")[0].id == contratante.id
        with pytest.raises(RegraDeNegocioErro):  # telefone de outro contratante
            sistema.contratantes.atualizar(contratante.id, telefone="(99) 99876-5432")
        with pytest.raises(ValidacaoErro):
            sistema.contratantes.atualizar(contratante.id, nome="")
        assert sistema.contratantes.obter(contratante.id).nome == "Maria S. Souza"

    def test_remover(self, sistema, contratante, outro_contratante, festa):
        sistema.contratantes.remover(outro_contratante.id)
        with pytest.raises(NaoEncontradoErro):
            sistema.contratantes.obter(outro_contratante.id)
        with pytest.raises(RegraDeNegocioErro, match="possui festas"):
            sistema.contratantes.remover(contratante.id)

    def test_nao_encontrado(self, sistema):
        with pytest.raises(NaoEncontradoErro):
            sistema.contratantes.obter(99)


class TesteServicoRecreador:
    def test_cadastro_listagem_e_disponibilidade(self, sistema):
        ana = sistema.recreadores.cadastrar("Ana Lima")
        sistema.recreadores.cadastrar("Bruno Costa")
        sistema.recreadores.definir_disponibilidade(ana.id, False)
        assert [r.identificacao for r in sistema.recreadores.listar()] == ["Ana Lima", "Bruno Costa"]
        assert [r.identificacao for r in sistema.recreadores.listar(apenas_disponiveis=True)] == ["Bruno Costa"]

    def test_duplicado_e_atualizar(self, sistema):
        ana = sistema.recreadores.cadastrar("Ana Lima")
        with pytest.raises(RegraDeNegocioErro):
            sistema.recreadores.cadastrar("ana lima")
        sistema.recreadores.atualizar(ana.id, "Ana Paula Lima")
        assert sistema.recreadores.obter(ana.id).identificacao == "Ana Paula Lima"

    def test_remover_recreador_em_festa_e_recusado(self, sistema, festa, recreadores):
        with pytest.raises(RegraDeNegocioErro, match="consta na festa"):
            sistema.recreadores.remover(recreadores[0].id)
        sistema.recreadores.remover(recreadores[5].id)  # sem festas
        with pytest.raises(NaoEncontradoErro):
            sistema.recreadores.obter(recreadores[5].id)


# ==========================================================================
# CT-02 / RF-02 — Registro da festa e campos obrigatórios
# ==========================================================================
class TesteAgendarFesta:
    def test_ct02_festa_completa_e_registrada(self, sistema, festa, contratante):
        assert festa.id == 1 and festa.contratante is contratante
        assert festa.situacao is SituacaoFesta.CONFIRMADA
        assert sistema.festas.obter(1) is festa
        assert len(festa.recreadores) == 2

    def test_ct02_campos_obrigatorios_impedem_o_cadastro(self, sistema, agendar):
        with pytest.raises(CampoObrigatorioErro) as erro:
            agendar(endereco=None, atividades=[], deslocamento="  ", recreadores_ids=[], data=None)
        assert set(erro.value.campos) == {
            "data", "endereço", "brincadeiras previstas", "recreadores escalados", "deslocamento",
        }
        assert "Campos obrigatórios" in str(erro.value)
        assert sistema.agenda.consultar().__len__() == 0  # nada foi gravado

    @pytest.mark.parametrize(
        "campo, rotulo",
        [
            ("contratante_id", "contratante"),
            ("inicio", "horário de início"),
            ("termino", "horário de término"),
            ("quantidade_criancas", "quantidade de crianças"),
            ("faixa_etaria", "faixa etária"),
            ("valor_combinado", "valor combinado"),
        ],
    )
    def test_ct02_cada_campo_obrigatorio_e_exigido(self, agendar, campo, rotulo):
        with pytest.raises(CampoObrigatorioErro) as erro:
            agendar(**{campo: None})
        assert rotulo in erro.value.campos

    def test_brinde_e_obrigatorio_a_partir_da_segunda_contratacao(self, sistema, festa, agendar):
        with pytest.raises(CampoObrigatorioErro) as erro:
            agendar(data=date(2027, 1, 10), brinde=None)
        assert "benefícios/brindes" in erro.value.campos

    def test_contratante_inexistente(self, agendar):
        with pytest.raises(NaoEncontradoErro):
            agendar(contratante_id=999)

    def test_recreador_inexistente_e_repetido(self, sistema, agendar):
        with pytest.raises(NaoEncontradoErro):
            agendar(recreadores_ids=[999])
        with pytest.raises(ValidacaoErro, match="repetido"):
            agendar(recreadores_ids=[1, 1])

    def test_data_anterior_a_confirmacao(self, agendar):
        with pytest.raises(ValidacaoErro, match="anterior"):
            agendar(data=HOJE - timedelta(days=1))

    def test_dados_invalidos_nao_gravam_nada(self, sistema, agendar):
        for mudanca in (dict(termino="13:00"), dict(quantidade_criancas=0), dict(valor_combinado="0")):
            with pytest.raises(ValidacaoErro):
                agendar(**mudanca)
        assert len(sistema.agenda.consultar()) == 0

    def test_nao_bloqueia_contratacao_proxima_da_data(self, agendar):
        """Fluxo 9.3: falta de antecedência não impede o registro."""
        assert agendar(data=HOJE + timedelta(days=2)).situacao is SituacaoFesta.CONFIRMADA

    def test_ids_sequenciais(self, sistema, agendar, recreadores):
        a = agendar()
        b = agendar(recreadores_ids=[recreadores[2].id], brinde="nenhum")
        assert (a.id, b.id) == (1, 2)


# ==========================================================================
# RN-08 — Brinde na primeira contratação
# ==========================================================================
class TesteBrindePrimeiraContratacao:
    def test_primeira_contratacao_recebe_brinde(self, festa):
        assert festa.detalhes.brinde == BRINDE_PRIMEIRA_CONTRATACAO
        assert festa.detalhes.tem_brinde

    def test_primeira_contratacao_sem_informar_brinde(self, agendar):
        assert agendar(brinde=None).detalhes.brinde == BRINDE_PRIMEIRA_CONTRATACAO

    def test_brinde_informado_e_mantido_junto_do_da_primeira_contratacao(self, agendar):
        assert agendar(brinde="Bolo de aniversário").detalhes.brinde == (
            f"Bolo de aniversário + {BRINDE_PRIMEIRA_CONTRATACAO}"
        )

    def test_segunda_contratacao_nao_recebe(self, sistema, festa, agendar):
        segunda = agendar(data=date(2027, 1, 10), brinde="não se aplica")
        assert segunda.detalhes.brinde == "não se aplica" and not segunda.detalhes.tem_brinde

    def test_cada_contratante_tem_sua_primeira_contratacao(self, sistema, festa, outro_contratante, agendar, recreadores):
        outra = agendar(contratante_id=outro_contratante.id, recreadores_ids=[recreadores[2].id], brinde=None)
        assert outra.detalhes.brinde == BRINDE_PRIMEIRA_CONTRATACAO


# ==========================================================================
# CT-03 / RF-03 — Agenda e situação
# ==========================================================================
class TesteAgenda:
    def test_ct03_consultar_agenda_e_situacoes(self, sistema, agendar, recreadores):
        a = agendar(data=date(2026, 12, 20))
        b = agendar(data=date(2026, 12, 10), recreadores_ids=[recreadores[2].id], brinde="n/a")
        c = agendar(data=date(2026, 12, 1), recreadores_ids=[recreadores[3].id], brinde="n/a")
        d = agendar(data=date(2026, 12, 5), recreadores_ids=[recreadores[4].id], brinde="n/a")

        sistema.financeiro.registrar_pagamento(c.id, "1000", HOJE)
        sistema.festas.marcar_realizada(c.id, date(2026, 12, 2))  # realizada e paga -> quitada
        sistema.financeiro.registrar_pagamento(d.id, "500", HOJE)
        sistema.festas.marcar_realizada(d.id, date(2026, 12, 6))  # realizada com saldo
        sistema.festas.cancelar(b.id, HOJE)

        agenda = sistema.agenda.consultar()
        assert isinstance(agenda, Agenda) and len(agenda) == 4
        assert [f.id for f in agenda] == [c.id, d.id, b.id, a.id]  # por data
        assert agenda[0] is c and c in agenda

        situacoes = {f.id: f.situacao for f in agenda}
        assert situacoes == {
            a.id: SituacaoFesta.CONFIRMADA,
            b.id: SituacaoFesta.CANCELADA,
            c.id: SituacaoFesta.QUITADA,
            d.id: SituacaoFesta.REALIZADA,
        }
        assert [f.id for f in sistema.agenda.consultar(situacao=SituacaoFesta.CANCELADA)] == [b.id]

    def test_filtros_por_periodo_e_dia(self, sistema, agendar, recreadores):
        agendar(data=date(2026, 12, 20))
        agendar(data=date(2027, 1, 10), recreadores_ids=[recreadores[2].id], brinde="n/a")
        assert len(sistema.agenda.consultar(data_inicial="01/01/2027")) == 1
        assert len(sistema.agenda.consultar(data_final="31/12/2026")) == 1
        assert len(sistema.agenda.do_dia("20/12/2026")) == 1
        assert len(sistema.agenda.do_dia("21/12/2026")) == 0
        assert "Agenda vazia" in str(sistema.agenda.do_dia("21/12/2026"))

    def test_proximas_apenas_confirmadas(self, sistema, agendar, recreadores):
        a = agendar(data=date(2026, 12, 20))
        b = agendar(data=date(2026, 12, 22), recreadores_ids=[recreadores[2].id], brinde="n/a")
        sistema.festas.cancelar(b.id, HOJE)
        assert [f.id for f in sistema.agenda.proximas(HOJE)] == [a.id]
        assert len(sistema.agenda.proximas(HOJE, limite=0)) == 0

    def test_agenda_funciona_como_sequencia(self, sistema, festa):
        agenda = sistema.agenda.consultar()
        assert len(agenda) == 1 and list(agenda) == [festa] and "Festa #1" in str(agenda)
        assert len(agenda.do_dia(DATA_FESTA)) == 1
        assert len(agenda.com_situacao(SituacaoFesta.QUITADA)) == 0
        assert "Agenda(1 festas)" == repr(agenda)


# ==========================================================================
# CT-04 / RF-04 / RN-05 / RN-07 — Recreadores, conflitos e simultaneidade
# ==========================================================================
class TesteEscala:
    def test_ct04_sobreposicao_e_sinalizada(self, sistema, festa, agendar, recreadores):
        with pytest.raises(ConflitoEscalaErro) as erro:
            agendar(inicio="15:00", termino="18:00", recreadores_ids=[recreadores[0].id], brinde="n/a")
        assert erro.value.conflitos[0].tipo is TipoConflito.SOBREPOSICAO
        assert "Ana Lima" in str(erro.value) and "mesmo horário" in str(erro.value)

    def test_ct04_festas_simultaneas_com_equipes_distintas(self, sistema, festa, agendar, recreadores):
        """Eventos simultâneos são permitidos quando há equipes disponíveis (RN-05)."""
        simultanea = agendar(
            recreadores_ids=[recreadores[2].id, recreadores[3].id], brinde="n/a"
        )  # mesmo dia e horário
        assert simultanea.data == festa.data and simultanea.inicio == festa.inicio
        assert simultanea.id != festa.id

    def test_decisao_final_e_da_gestora(self, sistema, festa, agendar, recreadores):
        forcada = agendar(
            inicio="15:00", termino="18:00", recreadores_ids=[recreadores[0].id], brinde="n/a",
            forcar_escala=True,
        )
        assert recreadores[0] in forcada.recreadores and recreadores[0] in festa.recreadores

    def test_intervalo_minimo_de_60_minutos(self, sistema, festa, agendar, recreadores):
        """RN-07: 60 min entre duas festas do mesmo recreador no mesmo dia."""
        ana = [recreadores[0].id]
        assert INTERVALO_MINIMO == timedelta(minutes=60)
        # termina às 17:00 -> 17:30 dá só 30 min
        with pytest.raises(ConflitoEscalaErro) as erro:
            agendar(inicio="17:30", termino="19:00", recreadores_ids=ana, brinde="n/a")
        assert erro.value.conflitos[0].tipo is TipoConflito.INTERVALO_INSUFICIENTE
        assert "menos de 60 min" in str(erro.value)
        # exatamente 60 min é permitido (17:00 -> 18:00)
        agendar(inicio="18:00", termino="20:00", recreadores_ids=ana, brinde="n/a")
        # antes da festa das 14:00: termina 13:30 -> 30 min; termina 13:00 -> 60 min
        with pytest.raises(ConflitoEscalaErro):
            agendar(inicio="10:00", termino="13:30", recreadores_ids=ana, brinde="n/a")
        agendar(inicio="10:00", termino="13:00", recreadores_ids=ana, brinde="n/a")

    def test_outro_dia_nao_conflita(self, sistema, festa, agendar, recreadores):
        agendar(data=DATA_FESTA + timedelta(days=1), recreadores_ids=[recreadores[0].id], brinde="n/a")

    def test_festa_cancelada_nao_gera_conflito(self, sistema, festa, agendar, recreadores):
        sistema.festas.cancelar(festa.id, HOJE)
        agendar(recreadores_ids=[recreadores[0].id], brinde="n/a")

    def test_recreador_indisponivel_e_sinalizado(self, sistema, agendar, recreadores):
        sistema.recreadores.definir_disponibilidade(recreadores[0].id, False)
        with pytest.raises(ConflitoEscalaErro) as erro:
            agendar()
        assert erro.value.conflitos[0].tipo is TipoConflito.INDISPONIVEL
        assert "indisponível" in str(erro.value)

    def test_alocar_com_alerta_e_confirmacao(self, sistema, festa, agendar, recreadores):
        outra = agendar(
            inicio="15:00", termino="18:00",
            recreadores_ids=[recreadores[2].id], brinde="n/a",
        )
        with pytest.raises(ConflitoEscalaErro):
            sistema.escala.alocar(outra.id, recreadores[0].id)
        assert recreadores[0] not in outra.recreadores  # alerta não altera a escala
        conflitos = sistema.escala.alocar(outra.id, recreadores[0].id, forcar=True)
        assert conflitos[0].tipo is TipoConflito.SOBREPOSICAO
        assert recreadores[0] in outra.recreadores

    def test_alocar_sem_conflito_e_desalocar(self, sistema, festa, recreadores):
        assert sistema.escala.alocar(festa.id, recreadores[4].id) == []
        assert recreadores[4] in festa.recreadores
        sistema.escala.desalocar(festa.id, recreadores[4].id)
        assert recreadores[4] not in festa.recreadores
        with pytest.raises(RegraDeNegocioErro):
            sistema.escala.desalocar(festa.id, recreadores[4].id)

    def test_alocar_duas_vezes_e_recusado(self, sistema, festa, recreadores):
        with pytest.raises(RegraDeNegocioErro, match="já está escalado"):
            sistema.escala.alocar(festa.id, recreadores[0].id)

    def test_recreadores_disponiveis_para_a_festa(self, sistema, festa, recreadores):
        outros = sistema.escala.recreadores_disponiveis(festa)
        assert {r.identificacao for r in outros} == {"Camila Rocha", "Diego Alves", "Elisa Prado", "Felipe Nunes"}

    def test_dimensionamento_alerta_equipe_abaixo_do_informado(self, sistema, agendar, recreadores):
        """RN-06: até 50 crianças de 5 a 12 anos -> 6 a 7 recreadores."""
        festa = agendar(quantidade_criancas=30, faixa_etaria=(5, 12))
        assert sistema.escala.recomendar(festa) == (6, 7)
        alertas = sistema.escala.alertas_equipe(festa)
        assert alertas and "abaixo" in alertas[0] and "6 a 7" in alertas[0]
        for recreador in recreadores[2:6]:
            sistema.escala.alocar(festa.id, recreador.id)
        assert sistema.escala.alertas_equipe(festa) == []

    def test_dimensionamento_alerta_equipe_acima_e_sem_referencia(self, sistema, agendar):
        festa = agendar(quantidade_criancas=5, faixa_etaria=(4, 9))  # informado: 2
        sistema.escala.alocar(festa.id, 3)
        assert "acima" in sistema.escala.alertas_equipe(festa)[0]
        sem_referencia = agendar(
            quantidade_criancas=80, faixa_etaria=(4, 9), data=DATA_FESTA + timedelta(days=3),
            brinde="n/a",
        )
        assert sistema.escala.recomendar(sem_referencia) is None
        assert sistema.escala.alertas_equipe(sem_referencia) == []


# ==========================================================================
# CT-05 / RF-05 — Crianças e atividades
# ==========================================================================
class TesteCriancasEAtividades:
    def test_ct05_registrar_e_consultar(self, festa):
        assert festa.quantidade_criancas == 8
        assert festa.faixa_etaria == FaixaEtaria(4, 9)
        assert [a.nome for a in festa.atividades] == ["Pintura facial", "Caça ao tesouro"]

    def test_atualizar(self, sistema, festa):
        sistema.festas.atualizar_criancas_e_atividades(
            festa.id, quantidade_criancas=12, faixa_etaria="6-10", atividades=["Gincana"]
        )
        assert (festa.quantidade_criancas, str(festa.faixa_etaria)) == (12, "6 a 10 anos")
        assert [a.nome for a in festa.atividades] == ["Gincana"]

    def test_atualizar_invalido_nao_altera_nada(self, sistema, festa):
        with pytest.raises(ValidacaoErro):
            sistema.festas.atualizar_criancas_e_atividades(festa.id, quantidade_criancas=0, atividades=["X"])
        with pytest.raises(ValidacaoErro):
            sistema.festas.atualizar_criancas_e_atividades(festa.id, atividades=[])
        assert festa.quantidade_criancas == 8 and len(festa.atividades) == 2

    def test_rn01_alerta_quando_atividade_nao_serve_para_a_faixa(self, sistema, agendar):
        festa = agendar(atividades=["Pintura", Atividade("Futebol", FaixaEtaria(8, 12))])
        resumo = sistema.resumos.gerar(festa.id)
        assert any("Futebol" in alerta for alerta in resumo.alertas)


# ==========================================================================
# CT-06 / RF-06 / RN-02 / RN-10 — Valores e pagamentos
# ==========================================================================
class TesteFinanceiro:
    def test_ct06_entrada_e_saldo_do_exemplo(self, sistema, festa):
        assert festa.valor_combinado == Decimal("1000.00")
        assert festa.entrada_prevista == Decimal("500.00")
        sistema.financeiro.registrar_pagamento(festa.id, "500", HOJE)
        assert sistema.financeiro.saldo_pendente(festa.id) == Decimal("500.00")
        sistema.festas.marcar_realizada(festa.id, DATA_FESTA)
        sistema.financeiro.registrar_pagamento(festa.id, "500", DATA_FESTA)
        assert sistema.financeiro.saldo_pendente(festa.id) == Decimal("0.00")
        assert festa.situacao is SituacaoFesta.QUITADA

    def test_pagamento_acima_do_saldo_nao_altera_o_estado(self, sistema, festa):
        with pytest.raises(ValidacaoErro):
            sistema.financeiro.registrar_pagamento(festa.id, "1000,01", HOJE)
        assert festa.pagamentos == () and festa.saldo_pendente == Decimal("1000.00")

    def test_saldo_sempre_igual_ao_valor_menos_pagamentos(self, sistema, festa):
        """CS-05."""
        for valor in ("100", "250,50", "149,50"):
            sistema.financeiro.registrar_pagamento(festa.id, valor, HOJE)
            assert festa.saldo_pendente == festa.valor_combinado - sum(
                (p.valor_recebido for p in festa.pagamentos), Decimal("0.00")
            )
        assert festa.pagamentos[-1].saldo_pendente == festa.saldo_pendente == Decimal("500.00")

    def test_situacao_por_contratante_e_total_a_receber(self, sistema, festa, outro_contratante, agendar, recreadores):
        outra = agendar(
            contratante_id=outro_contratante.id, valor_combinado="2400",
            recreadores_ids=[recreadores[2].id], brinde=None,
        )
        sistema.financeiro.registrar_pagamento(festa.id, "500", HOJE)
        sistema.financeiro.registrar_pagamento(outra.id, "1200", HOJE)
        linhas = sistema.financeiro.situacao_por_contratante()
        assert [l.contratante.nome for l in linhas] == ["João Pereira", "Maria Souza"]
        joao, maria = linhas
        assert (joao.total_contratado, joao.total_recebido, joao.saldo_pendente) == (
            Decimal("2400.00"), Decimal("1200.00"), Decimal("1200.00"),
        )
        assert maria.saldo_pendente == Decimal("500.00") and maria.quantidade_festas == 1
        assert sistema.financeiro.total_a_receber() == Decimal("1700.00")
        assert "R$ 1.200,00" in str(joao)

    def test_festa_cancelada_sai_do_a_receber_e_vira_credito(self, sistema, festa):
        """RN-03: valor pago retido, utilizável em até 1 ano."""
        sistema.financeiro.registrar_pagamento(festa.id, "500", HOJE)
        sistema.festas.cancelar(festa.id, date(2026, 12, 1))
        assert sistema.financeiro.total_a_receber() == Decimal("0.00")
        creditos = sistema.financeiro.creditos_retidos(date(2027, 6, 1))
        assert len(creditos) == 1
        assert creditos[0].valor == Decimal("500.00") and creditos[0].valido_ate == date(2027, 12, 1)
        assert "R$ 500,00" in str(creditos[0])
        assert sistema.financeiro.creditos_retidos(date(2027, 12, 2)) == []  # expirou

    def test_data_so_fica_reservada_apos_a_entrada(self, sistema, festa):
        """RN-02."""
        assert not festa.data_reservada
        sistema.financeiro.registrar_pagamento(festa.id, "500", HOJE)
        assert festa.data_reservada
        assert "reservada" in str(sistema.resumos.gerar(festa.id))


# ==========================================================================
# CT-07 / RF-07 — Benefícios e deslocamento
# ==========================================================================
class TesteDetalhes:
    def test_ct07_registrar_e_consultar(self, sistema, agendar, outro_contratante, recreadores):
        festa = agendar(
            contratante_id=outro_contratante.id, brinde="Bolo", deslocamento="Outra cidade — Riachão, ~80 km",
            recreadores_ids=[recreadores[2].id],
        )
        assert festa.detalhes.deslocamento == "Outra cidade — Riachão, ~80 km"
        assert festa.detalhes.tem_deslocamento
        assert "Bolo" in festa.detalhes.brinde

    def test_atualizar_detalhes(self, sistema, festa):
        sistema.festas.atualizar_detalhes(festa.id, deslocamento="Outra cidade — 50 km")
        assert festa.detalhes.deslocamento == "Outra cidade — 50 km"
        assert festa.detalhes.brinde == BRINDE_PRIMEIRA_CONTRATACAO  # mantido
        with pytest.raises(ValidacaoErro):
            sistema.festas.atualizar_detalhes(festa.id, brinde=" ")
        assert festa.detalhes.deslocamento == "Outra cidade — 50 km"


# ==========================================================================
# CT-08 / RF-08 / RN-09 — Avisos
# ==========================================================================
class TesteAvisos:
    def test_ct08_confirmacao_14_dias_e_7_dias(self, festa):
        """Festa a 26 dias: aviso na confirmação, lembrete 14 e 7 dias antes."""
        assert datas_por_tipo(festa) == {
            TipoLembrete.CONFIRMACAO: HOJE,
            TipoLembrete.LEMBRETE_14_DIAS: date(2026, 12, 6),
            TipoLembrete.LEMBRETE_7_DIAS: date(2026, 12, 13),
        }
        assert all(l.situacao is SituacaoLembrete.PENDENTE for l in festa.lembretes)

    def test_ct08_contratacao_com_menos_de_14_dias_avisa_imediatamente(self, agendar):
        festa = agendar(data=HOJE + timedelta(days=10))
        assert datas_por_tipo(festa) == {
            TipoLembrete.CONFIRMACAO: HOJE,
            TipoLembrete.AVISO_IMEDIATO: HOJE,
            TipoLembrete.LEMBRETE_7_DIAS: HOJE + timedelta(days=3),
        }

    def test_exatamente_14_dias_ainda_e_lembrete_de_14(self, agendar):
        festa = agendar(data=HOJE + timedelta(days=14))
        assert datas_por_tipo(festa)[TipoLembrete.LEMBRETE_14_DIAS] == HOJE
        assert TipoLembrete.AVISO_IMEDIATO not in tipos(festa)

    def test_13_dias_ja_e_aviso_imediato(self, agendar):
        festa = agendar(data=HOJE + timedelta(days=13))
        assert TipoLembrete.AVISO_IMEDIATO in tipos(festa)
        assert TipoLembrete.LEMBRETE_14_DIAS not in tipos(festa)

    def test_festa_em_menos_de_7_dias_nao_tem_lembrete_de_7(self, agendar):
        festa = agendar(data=HOJE + timedelta(days=4))
        assert TipoLembrete.LEMBRETE_7_DIAS not in tipos(festa)
        assert TipoLembrete.AVISO_IMEDIATO in tipos(festa)

    def test_exatamente_7_dias_gera_lembrete_no_proprio_dia(self, agendar):
        festa = agendar(data=HOJE + timedelta(days=7))
        assert datas_por_tipo(festa)[TipoLembrete.LEMBRETE_7_DIAS] == HOJE

    def test_avisos_aparecem_nas_datas_previstas(self, sistema, festa):
        def tipos_em(dia):
            return [a.lembrete.tipo for a in sistema.lembretes.avisos_pendentes(dia)]

        assert tipos_em(date(2026, 11, 23)) == []
        assert tipos_em(HOJE) == [TipoLembrete.CONFIRMACAO]
        assert tipos_em(date(2026, 12, 5)) == [TipoLembrete.CONFIRMACAO]
        assert tipos_em(date(2026, 12, 6)) == [TipoLembrete.CONFIRMACAO, TipoLembrete.LEMBRETE_14_DIAS]
        assert tipos_em(date(2026, 12, 13))[-1] is TipoLembrete.LEMBRETE_7_DIAS

    def test_envio_e_sempre_manual(self, sistema, festa):
        """O sistema só organiza: o aviso permanece pendente até Bruna marcar o envio."""
        assert sistema.lembretes.avisos_pendentes(DATA_FESTA)  # nada some sozinho
        assert all(l.pendente for l in festa.lembretes)
        aviso = sistema.lembretes.avisos_pendentes(HOJE)[0]
        sistema.lembretes.marcar_enviado(aviso.festa.id, aviso.indice, HOJE)
        assert festa.lembretes[aviso.indice].situacao is SituacaoLembrete.ENVIADO
        assert festa.lembretes[aviso.indice].data_envio == HOJE
        assert sistema.lembretes.avisos_pendentes(HOJE) == []
        assert HORARIO_PREFERIDO_ENVIO.hour == 9
        assert "até 09:00" in str(aviso)

    def test_marcar_enviado_aviso_inexistente_ou_repetido(self, sistema, festa):
        with pytest.raises(NaoEncontradoErro):
            sistema.lembretes.marcar_enviado(festa.id, 99)
        sistema.lembretes.marcar_enviado(festa.id, 0, HOJE)
        with pytest.raises(RegraDeNegocioErro):
            sistema.lembretes.marcar_enviado(festa.id, 0, HOJE)

    def test_festa_cancelada_some_dos_avisos(self, sistema, festa):
        sistema.festas.cancelar(festa.id, HOJE)
        assert sistema.lembretes.avisos_pendentes(DATA_FESTA) == []
        assert set(tipos(festa, SituacaoLembrete.CANCELADO)) == {
            TipoLembrete.CONFIRMACAO, TipoLembrete.LEMBRETE_14_DIAS, TipoLembrete.LEMBRETE_7_DIAS,
        }

    def test_polimorfismo_regras_de_aviso_substituiveis(self, sistema, contratante, recreadores, dados_festa):
        """O serviço usa qualquer RegraDeAviso: aqui, só o aviso de confirmação."""
        servico = ServicoLembrete(sistema.armazenamento, regras=[AvisoConfirmacao()])
        sistema.festas._lembretes = servico  # injeta o serviço com outras regras
        festa = sistema.festas.agendar(**dados_festa)
        assert tipos(festa) == [TipoLembrete.CONFIRMACAO]
        assert issubclass(AvisoConfirmacao, RegraDeAviso)
        with pytest.raises(TypeError):
            RegraDeAviso()  # type: ignore[abstract]


# ==========================================================================
# CT-09 / RN-04 / RN-09 — Remarcação
# ==========================================================================
class TesteRemarcacao:
    def test_ct09_alterar_data_refaz_os_lembretes(self, sistema, festa):
        remarcada = sistema.festas.remarcar(festa.id, date(2027, 1, 10), data_remarcacao=date(2026, 12, 1))
        assert remarcada.data == date(2027, 1, 10)
        # avisos antigos de 14 e 7 dias foram cancelados; a confirmação original permanece
        assert set(tipos(festa, SituacaoLembrete.CANCELADO)) == {
            TipoLembrete.LEMBRETE_14_DIAS, TipoLembrete.LEMBRETE_7_DIAS,
        }
        assert datas_por_tipo(festa) == {
            TipoLembrete.CONFIRMACAO: HOJE,
            TipoLembrete.LEMBRETE_14_DIAS: date(2026, 12, 27),
            TipoLembrete.LEMBRETE_7_DIAS: date(2027, 1, 3),
        }
        assert len(festa.lembretes) == 5

    def test_remarcar_para_data_proxima_gera_aviso_imediato(self, sistema, festa):
        sistema.festas.remarcar(festa.id, date(2026, 12, 5), data_remarcacao=date(2026, 11, 30))
        pendentes = datas_por_tipo(festa)
        assert pendentes[TipoLembrete.AVISO_IMEDIATO] == date(2026, 11, 30)
        assert TipoLembrete.LEMBRETE_14_DIAS not in pendentes
        assert TipoLembrete.LEMBRETE_7_DIAS not in pendentes  # faltam menos de 7 dias

    def test_remarcar_pode_mudar_o_horario(self, sistema, festa):
        sistema.festas.remarcar(festa.id, DATA_FESTA, inicio="10:00", termino="12:00", data_remarcacao=HOJE)
        assert str(festa.inicio) == "10:00:00" and str(festa.termino) == "12:00:00"

    def test_aviso_ja_enviado_e_preservado_na_remarcacao(self, sistema, festa):
        sistema.lembretes.marcar_enviado(festa.id, 1, HOJE)  # lembrete de 14 dias já enviado
        sistema.festas.remarcar(festa.id, date(2027, 1, 10), data_remarcacao=date(2026, 12, 1))
        assert festa.lembretes[1].situacao is SituacaoLembrete.ENVIADO

    def test_remarcar_valida_data_horario_e_situacao(self, sistema, festa):
        with pytest.raises(ValidacaoErro, match="anterior"):
            sistema.festas.remarcar(festa.id, date(2026, 11, 1), data_remarcacao=HOJE)
        with pytest.raises(ValidacaoErro):
            sistema.festas.remarcar(festa.id, DATA_FESTA, inicio="18:00", data_remarcacao=HOJE)
        assert festa.data == DATA_FESTA
        sistema.festas.cancelar(festa.id, HOJE)
        with pytest.raises(TransicaoInvalidaErro):
            sistema.festas.remarcar(festa.id, date(2027, 1, 10), data_remarcacao=HOJE)

    def test_remarcar_sinaliza_conflito_de_escala(self, sistema, festa, agendar, recreadores):
        outra = agendar(
            data=date(2027, 1, 10), recreadores_ids=[recreadores[2].id, recreadores[0].id], brinde="n/a"
        )
        with pytest.raises(ConflitoEscalaErro):  # Ana já está na outra festa nesse dia
            sistema.festas.remarcar(festa.id, date(2027, 1, 10), data_remarcacao=HOJE)
        assert festa.data == DATA_FESTA  # nada mudou
        sistema.festas.remarcar(festa.id, date(2027, 1, 10), data_remarcacao=HOJE, forcar_escala=True)
        assert festa.data == outra.data

    def test_remarcar_nao_conflita_com_a_propria_festa(self, sistema, festa):
        sistema.festas.remarcar(festa.id, DATA_FESTA, inicio="15:00", termino="18:00", data_remarcacao=HOJE)


# ==========================================================================
# Situação e cancelamento (serviço)
# ==========================================================================
class TesteSituacaoServico:
    def test_marcar_realizada_e_cancelar(self, sistema, festa):
        with pytest.raises(RegraDeNegocioErro):
            sistema.festas.marcar_realizada(festa.id, HOJE)  # festa ainda é futura
        sistema.festas.marcar_realizada(festa.id, DATA_FESTA)
        assert festa.situacao is SituacaoFesta.REALIZADA
        with pytest.raises(TransicaoInvalidaErro):
            sistema.festas.cancelar(festa.id, DATA_FESTA)

    def test_festas_do_contratante(self, sistema, festa, outro_contratante, agendar, recreadores):
        segunda = agendar(data=date(2027, 1, 10), brinde="n/a")
        outra = agendar(contratante_id=outro_contratante.id, recreadores_ids=[recreadores[2].id])
        assert sistema.festas.festas_do_contratante(festa.contratante.id) == [festa, segunda]
        assert sistema.festas.festas_do_contratante(outro_contratante.id) == [outra]


# ==========================================================================
# CT-10 / RF-09 — Resumo do evento
# ==========================================================================
class TesteResumo:
    def test_ct10_resumo_reune_tudo(self, sistema, festa):
        sistema.financeiro.registrar_pagamento(festa.id, "500", HOJE)
        texto = str(sistema.resumos.gerar(festa.id))
        for esperado in (
            "FESTA #1", "CONFIRMADA",
            "Maria Souza", "(99) 98123-4567",  # contratante
            "20/12/2026", "14:00 às 17:00", "Rua das Flores", "8 (4 a 9 anos)",  # programação
            "Pintura facial", "Caça ao tesouro",
            "Ana Lima", "Bruno Costa",  # equipe
            "R$ 1.000,00", "R$ 500,00",  # valores
            "Aviso de confirmação", "Lembrete de 14 dias", "Lembrete de 7 dias",  # avisos
            BRINDE_PRIMEIRA_CONTRATACAO, "não se aplica",  # detalhes
        ):
            assert esperado in texto, esperado
        assert "Data reservada (entrada paga): sim" in texto

    def test_resumo_traz_alertas(self, sistema, agendar):
        festa = agendar(quantidade_criancas=30, faixa_etaria=(5, 12))
        resumo = sistema.resumos.gerar(festa.id)
        assert any("abaixo" in a for a in resumo.alertas)
        assert any("Entrada ainda não recebida" in a for a in resumo.alertas)
        assert "ALERTAS" in str(resumo)

    def test_resumo_alerta_saldo_pendente_apos_festa_realizada(self, sistema, festa):
        sistema.festas.marcar_realizada(festa.id, DATA_FESTA)
        assert any("saldo pendente" in a for a in sistema.resumos.gerar(festa.id).alertas)

    def test_resumo_de_festa_cancelada_mostra_credito(self, sistema, festa):
        sistema.financeiro.registrar_pagamento(festa.id, "500", HOJE)
        sistema.festas.cancelar(festa.id, date(2026, 12, 1))
        resumo = sistema.resumos.gerar(festa.id)
        assert "Crédito retido: R$ 500,00 válido até 01/12/2027" in str(resumo)
        assert resumo.alertas == []

    def test_resumo_de_combinacao_sem_referencia(self, sistema, agendar):
        festa = agendar(quantidade_criancas=80)
        assert "critério da gestora" in str(sistema.resumos.gerar(festa.id))

    def test_resumo_de_festa_inexistente(self, sistema):
        with pytest.raises(NaoEncontradoErro):
            sistema.resumos.gerar(99)

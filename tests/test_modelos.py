"""Testes das classes do modelo: criação, validações, encapsulamento, herança,
polimorfismo, métodos especiais e conversão de/para dicionário."""

from datetime import date, time
from decimal import Decimal

import pytest

from docinho.excecoes import (
    RegraDeNegocioErro,
    TransicaoInvalidaErro,
    ValidacaoErro,
)
from docinho.modelos import (
    Atividade,
    Contratante,
    DetalhesComplementares,
    EntidadeBase,
    FaixaEtaria,
    Festa,
    Lembrete,
    Recreador,
    RegistroPagamento,
    SituacaoFesta,
    SituacaoLembrete,
    TipoLembrete,
    recomendar_equipe,
)
from docinho.validacao import (
    moeda,
    normalizar_telefone,
    para_data,
    para_decimal,
    para_hora,
    somar_um_ano,
)

HOJE = date(2026, 11, 24)


def nova_festa(contratante=None, **mudancas):
    contratante = contratante or Contratante("Maria Souza", "99981234567", id=1)
    dados = dict(
        contratante=contratante,
        data=date(2026, 12, 20),
        inicio="14:00",
        termino="17:00",
        endereco="Rua das Flores, 120",
        quantidade_criancas=8,
        faixa_etaria=(4, 9),
        valor_combinado="1000.00",
        atividades=["Pintura facial"],
        detalhes=DetalhesComplementares("não se aplica", "não se aplica"),
        data_confirmacao=HOJE,
    )
    dados.update(mudancas)
    return Festa(**dados)


# --------------------------------------------------------------------------
# Funções de validação
# --------------------------------------------------------------------------
class TesteValidacao:
    @pytest.mark.parametrize(
        "entrada",
        ["(99) 98123-4567", "99 98123 4567", "+55 99 98123-4567", "99981234567"],
    )
    def test_telefone_aceita_formatos_comuns(self, entrada):
        assert normalizar_telefone(entrada) == "99981234567"

    @pytest.mark.parametrize("entrada", ["", "123", "(99) 1234", "abc", None, "999999999999999"])
    def test_telefone_invalido(self, entrada):
        with pytest.raises(ValidacaoErro):
            normalizar_telefone(entrada)

    def test_decimal_formatos_brasileiros(self):
        assert para_decimal("1.234,56") == Decimal("1234.56")
        assert para_decimal("R$ 500,00") == Decimal("500.00")
        assert para_decimal(1000) == Decimal("1000.00")
        assert para_decimal(0.1) == Decimal("0.10")

    @pytest.mark.parametrize("entrada", ["abc", "", None, True, "NaN"])
    def test_decimal_invalido(self, entrada):
        with pytest.raises(ValidacaoErro):
            para_decimal(entrada)

    def test_data_e_hora(self):
        assert para_data("20/12/2026") == date(2026, 12, 20)
        assert para_data("2026-12-20") == date(2026, 12, 20)
        assert para_hora("14:30") == time(14, 30)
        with pytest.raises(ValidacaoErro):
            para_data("31/02/2026")
        with pytest.raises(ValidacaoErro):
            para_hora("25:00")

    def test_um_ano_inclui_ano_bissexto(self):
        assert somar_um_ano(date(2026, 11, 24)) == date(2027, 11, 24)
        assert somar_um_ano(date(2028, 2, 29)) == date(2029, 2, 28)

    def test_moeda_padrao_brasileiro(self):
        assert moeda(1000) == "R$ 1.000,00"
        assert moeda("1234.5") == "R$ 1.234,50"


# --------------------------------------------------------------------------
# Abstração e herança
# --------------------------------------------------------------------------
class TesteAbstracaoEHeranca:
    def test_entidade_base_e_abstrata(self):
        with pytest.raises(TypeError):
            EntidadeBase()  # type: ignore[abstract]

    @pytest.mark.parametrize("classe", [Contratante, Recreador, Festa])
    def test_entidades_herdam_da_base(self, classe):
        assert issubclass(classe, EntidadeBase)

    def test_id_so_pode_ser_atribuido_uma_vez(self):
        contratante = Contratante("Maria", "99981234567")
        contratante.atribuir_id(1)
        contratante.atribuir_id(1)  # repetir o mesmo valor é inofensivo
        with pytest.raises(ValueError):
            contratante.atribuir_id(2)


# --------------------------------------------------------------------------
# Contratante
# --------------------------------------------------------------------------
class TesteContratante:
    def test_criacao_normaliza_dados(self):
        c = Contratante("  Maria   Souza ", "(99) 98123-4567")
        assert c.nome == "Maria Souza"
        assert c.telefone == "99981234567"
        assert c.telefone_formatado == "(99) 98123-4567"

    def test_nome_obrigatorio(self):
        with pytest.raises(ValidacaoErro):
            Contratante("   ", "99981234567")
        with pytest.raises(ValidacaoErro):
            Contratante("M", "99981234567")

    def test_encapsulamento_valida_alteracoes(self):
        c = Contratante("Maria", "99981234567")
        with pytest.raises(ValidacaoErro):
            c.telefone = "123"
        assert c.telefone == "99981234567"  # valor anterior preservado
        c.telefone = "(99) 3333-4444"
        assert c.telefone == "9933334444"
        assert c.telefone_formatado == "(99) 3333-4444"

    def test_dunder_str_repr_eq(self):
        a = Contratante("Maria Souza", "(99) 98123-4567", id=3)
        b = Contratante("Maria S.", "99981234567")
        assert str(a) == "Maria Souza — (99) 98123-4567"
        assert "Maria Souza" in repr(a) and "id=3" in repr(a)
        assert a == b  # mesmo telefone = mesma pessoa
        assert a != Contratante("Maria Souza", "99981234568")
        assert a != "Maria Souza"

    def test_ida_e_volta_dicionario(self):
        original = Contratante("Maria Souza", "99981234567", id=7)
        copia = Contratante.de_dicionario(original.para_dicionario())
        assert copia == original and copia.id == 7 and copia.nome == "Maria Souza"


# --------------------------------------------------------------------------
# Recreador
# --------------------------------------------------------------------------
class TesteRecreador:
    def test_criacao_e_disponibilidade(self):
        r = Recreador("Ana Lima")
        assert r.identificacao == "Ana Lima" and r.disponibilidade is True
        r.disponibilidade = False
        assert "indisponível" in str(r)

    def test_validacoes(self):
        with pytest.raises(ValidacaoErro):
            Recreador("  ")
        with pytest.raises(ValidacaoErro):
            Recreador("Ana", disponivel="sim")  # type: ignore[arg-type]

    def test_igualdade_ignora_acento_e_caixa(self):
        assert Recreador("João Alves") == Recreador("joao alves")
        assert Recreador("João") != Recreador("Joana")

    def test_ida_e_volta_dicionario(self):
        original = Recreador("Ana Lima", disponivel=False, id=2)
        copia = Recreador.de_dicionario(original.para_dicionario())
        assert copia == original and copia.disponibilidade is False and copia.id == 2


# --------------------------------------------------------------------------
# Objetos de valor e componentes
# --------------------------------------------------------------------------
class TesteFaixaEtaria:
    def test_validacao(self):
        with pytest.raises(ValidacaoErro):
            FaixaEtaria(10, 5)
        with pytest.raises(ValidacaoErro):
            FaixaEtaria(-1, 5)
        with pytest.raises(ValidacaoErro):
            FaixaEtaria(3, 30)
        with pytest.raises(ValidacaoErro):
            FaixaEtaria("3", 5)  # type: ignore[arg-type]

    def test_dunder_contains_eq_str(self):
        faixa = FaixaEtaria(5, 9)
        assert 7 in faixa and 10 not in faixa and 5 in faixa and 9 in faixa
        assert faixa == FaixaEtaria(5, 9) and faixa != FaixaEtaria(5, 10)
        assert str(faixa) == "5 a 9 anos" and str(FaixaEtaria(6, 6)) == "6 anos"
        assert repr(faixa) == "FaixaEtaria(5, 9)"

    def test_cobre_outra_faixa(self):
        assert FaixaEtaria(3, 12).cobre(FaixaEtaria(4, 9))
        assert not FaixaEtaria(10, 12).cobre(FaixaEtaria(8, 11))

    @pytest.mark.parametrize("valor", ["5-9", "5 a 9", (5, 9), [5, 9], {"idade_minima": 5, "idade_maxima": 9}])
    def test_conversao(self, valor):
        assert FaixaEtaria.de(valor) == FaixaEtaria(5, 9)

    def test_conversao_invalida(self):
        with pytest.raises(ValidacaoErro):
            FaixaEtaria.de("abc")


class TesteAtividade:
    def test_sem_indicacao_serve_para_qualquer_faixa(self):
        assert Atividade("Pintura facial").adequada_para(FaixaEtaria(3, 12))

    def test_com_indicacao(self):
        atividade = Atividade("Futebol", FaixaEtaria(8, 12))
        assert atividade.adequada_para(FaixaEtaria(9, 11))
        assert not atividade.adequada_para(FaixaEtaria(4, 9))
        assert str(atividade) == "Futebol (8 a 12 anos)"

    def test_nome_obrigatorio_e_ida_e_volta(self):
        with pytest.raises(ValidacaoErro):
            Atividade("")
        original = Atividade("Futebol", FaixaEtaria(8, 12))
        assert Atividade.de_dicionario(original.para_dicionario()) == original


class TesteDetalhes:
    def test_campos_obrigatorios(self):
        with pytest.raises(ValidacaoErro):
            DetalhesComplementares("", "não se aplica")
        with pytest.raises(ValidacaoErro):
            DetalhesComplementares("Bolo", " ")

    def test_nao_se_aplica(self):
        sem = DetalhesComplementares("Não se aplica", "NÃO SE APLICA")
        com = DetalhesComplementares("Kit festa", "Outra cidade — 80 km")
        assert not sem.tem_brinde and not sem.tem_deslocamento
        assert com.tem_brinde and com.tem_deslocamento

    def test_ida_e_volta(self):
        original = DetalhesComplementares("Kit festa", "Outra cidade")
        copia = DetalhesComplementares.de_dicionario(original.para_dicionario())
        assert (copia.brinde, copia.deslocamento) == ("Kit festa", "Outra cidade")


class TesteRegistroPagamento:
    def test_criacao(self):
        p = RegistroPagamento("500,00", HOJE, "500.00")
        assert p.valor_recebido == Decimal("500.00") and p.saldo_pendente == Decimal("500.00")
        assert "R$ 500,00" in str(p)

    def test_valores_invalidos(self):
        with pytest.raises(ValidacaoErro):
            RegistroPagamento(0, HOJE, 100)
        with pytest.raises(ValidacaoErro):
            RegistroPagamento(10, HOJE, -1)

    def test_ida_e_volta(self):
        original = RegistroPagamento("250.50", HOJE, "749.50")
        copia = RegistroPagamento.de_dicionario(original.para_dicionario())
        assert (copia.valor_recebido, copia.data_pagamento, copia.saldo_pendente) == (
            Decimal("250.50"), HOJE, Decimal("749.50"),
        )


class TesteLembrete:
    def test_marcar_enviado_e_cancelar(self):
        l = Lembrete(HOJE, TipoLembrete.CONFIRMACAO)
        assert l.pendente and l.deve_aparecer_em(HOJE)
        assert not l.deve_aparecer_em(date(2026, 11, 23))
        l.marcar_enviado(HOJE)
        assert l.situacao is SituacaoLembrete.ENVIADO and l.data_envio == HOJE
        assert not l.deve_aparecer_em(HOJE)
        with pytest.raises(RegraDeNegocioErro):
            l.marcar_enviado(HOJE)
        l.cancelar()  # já enviado: continua enviado
        assert l.situacao is SituacaoLembrete.ENVIADO

    def test_cancelar_pendente(self):
        l = Lembrete(HOJE, TipoLembrete.LEMBRETE_7_DIAS)
        l.cancelar()
        assert l.situacao is SituacaoLembrete.CANCELADO and not l.pendente

    def test_str_e_ida_e_volta(self):
        l = Lembrete(date(2026, 12, 6), TipoLembrete.LEMBRETE_14_DIAS)
        assert "06/12/2026" in str(l) and "14 dias" in str(l)
        copia = Lembrete.de_dicionario(l.para_dicionario())
        assert (copia.data_prevista, copia.tipo, copia.situacao) == (l.data_prevista, l.tipo, l.situacao)


# --------------------------------------------------------------------------
# Festa
# --------------------------------------------------------------------------
class TesteFestaCriacaoEValidacao:
    def test_criacao_valida(self):
        f = nova_festa()
        assert f.data == date(2026, 12, 20)
        assert (f.inicio, f.termino) == (time(14, 0), time(17, 0))
        assert f.quantidade_criancas == 8 and f.faixa_etaria == FaixaEtaria(4, 9)
        assert f.valor_combinado == Decimal("1000.00")
        assert f.situacao is SituacaoFesta.CONFIRMADA and f.confirmada
        assert [a.nome for a in f.atividades] == ["Pintura facial"]

    @pytest.mark.parametrize(
        "mudanca",
        [
            dict(termino="14:00"),
            dict(termino="13:00"),
            dict(endereco="  "),
            dict(quantidade_criancas=0),
            dict(quantidade_criancas=-3),
            dict(quantidade_criancas=2.5),
            dict(quantidade_criancas=True),
            dict(valor_combinado="0"),
            dict(valor_combinado="-10"),
            dict(valor_combinado="abc"),
            dict(atividades=[]),
            dict(faixa_etaria="abc"),
            dict(data="32/13/2026"),
            dict(detalhes="brinde"),
        ],
    )
    def test_dados_invalidos_sao_recusados(self, mudanca):
        with pytest.raises(ValidacaoErro):
            nova_festa(**mudanca)

    def test_exige_contratante(self):
        with pytest.raises(ValidacaoErro):
            nova_festa(contratante="Maria")

    def test_encapsulamento_setters_validam(self):
        f = nova_festa()
        with pytest.raises(ValidacaoErro):
            f.quantidade_criancas = 0
        assert f.quantidade_criancas == 8
        f.quantidade_criancas = 15
        f.endereco = "Nova rua, 5"
        assert (f.quantidade_criancas, f.endereco) == (15, "Nova rua, 5")
        with pytest.raises(ValidacaoErro):
            f.definir_horario("10:00", "09:00")
        assert (f.inicio, f.termino) == (time(14, 0), time(17, 0))

    def test_listas_expostas_nao_alteram_o_objeto(self):
        f = nova_festa()
        assert isinstance(f.recreadores, tuple) and isinstance(f.pagamentos, tuple)
        assert isinstance(f.lembretes, tuple) and isinstance(f.atividades, tuple)


class TesteFestaValores:
    def test_entrada_e_saldo_do_exemplo_da_srs(self):
        """RF-06 / CT-06: R$ 1.000,00 -> entrada R$ 500,00 e saldo inicial R$ 500,00."""
        f = nova_festa(valor_combinado="1000.00")
        assert f.entrada_prevista == Decimal("500.00")
        assert f.saldo_pendente == Decimal("1000.00") and not f.data_reservada
        f.registrar_pagamento("500.00", HOJE)
        assert f.saldo_pendente == Decimal("500.00") and f.entrada_paga and f.data_reservada
        f.registrar_pagamento("500.00", HOJE)
        assert f.saldo_pendente == Decimal("0.00")

    def test_entrada_arredonda_centavos(self):
        assert nova_festa(valor_combinado="333.33").entrada_prevista == Decimal("166.67")

    def test_pagamento_registra_saldo_apos_cada_recebimento(self):
        f = nova_festa()
        p1 = f.registrar_pagamento("300", HOJE)
        p2 = f.registrar_pagamento("200", HOJE)
        assert (p1.saldo_pendente, p2.saldo_pendente) == (Decimal("700.00"), Decimal("500.00"))
        assert f.total_recebido == Decimal("500.00") and len(f.pagamentos) == 2

    def test_pagamento_maior_que_saldo_e_recusado(self):
        f = nova_festa()
        f.registrar_pagamento("900", HOJE)
        with pytest.raises(ValidacaoErro, match="maior que o saldo"):
            f.registrar_pagamento("100,01", HOJE)
        assert f.saldo_pendente == Decimal("100.00")

    @pytest.mark.parametrize("valor", ["0", "-5", "abc"])
    def test_pagamento_invalido(self, valor):
        with pytest.raises(ValidacaoErro):
            nova_festa().registrar_pagamento(valor, HOJE)

    def test_valor_combinado_nao_fica_abaixo_do_recebido(self):
        f = nova_festa()
        f.registrar_pagamento("600", HOJE)
        with pytest.raises(ValidacaoErro):
            f.valor_combinado = "500"

    def test_data_reservada_somente_apos_entrada(self):
        """RN-02."""
        f = nova_festa()
        f.registrar_pagamento("499.99", HOJE)
        assert not f.data_reservada
        f.registrar_pagamento("0.01", HOJE)
        assert f.data_reservada


class TesteFestaSituacao:
    def test_ciclo_confirmada_realizada_quitada(self):
        f = nova_festa()
        f.registrar_pagamento("500", HOJE)
        f.marcar_realizada(date(2026, 12, 20))
        assert f.situacao is SituacaoFesta.REALIZADA
        f.registrar_pagamento("500", date(2026, 12, 20))
        assert f.situacao is SituacaoFesta.QUITADA

    def test_realizada_com_saldo_zero_ja_fica_quitada(self):
        f = nova_festa()
        f.registrar_pagamento("1000", HOJE)
        assert f.situacao is SituacaoFesta.CONFIRMADA  # ainda não aconteceu
        f.marcar_realizada(date(2026, 12, 21))
        assert f.situacao is SituacaoFesta.QUITADA

    def test_nao_marca_realizada_festa_futura(self):
        with pytest.raises(RegraDeNegocioErro, match="data futura"):
            nova_festa().marcar_realizada(date(2026, 12, 19))

    @pytest.mark.parametrize("acao", ["realizada_de_cancelada", "cancelar_realizada", "cancelar_quitada"])
    def test_transicoes_invalidas(self, acao):
        f = nova_festa()
        if acao == "realizada_de_cancelada":
            f.cancelar(HOJE)
            with pytest.raises(TransicaoInvalidaErro):
                f.marcar_realizada(date(2027, 1, 1))
        elif acao == "cancelar_realizada":
            f.marcar_realizada(date(2026, 12, 21))
            with pytest.raises(TransicaoInvalidaErro):
                f.cancelar(HOJE)
        else:
            f.registrar_pagamento("1000", HOJE)
            f.marcar_realizada(date(2026, 12, 21))
            with pytest.raises(TransicaoInvalidaErro):
                f.cancelar(HOJE)

    def test_cancelamento_retem_valor_por_um_ano(self):
        """RN-03."""
        f = nova_festa()
        f.registrar_pagamento("500", HOJE)
        f.cancelar(date(2026, 12, 1))
        assert f.situacao is SituacaoFesta.CANCELADA
        assert f.credito_retido == Decimal("500.00")
        assert f.credito_valido_ate == date(2027, 12, 1)
        assert f.data_cancelamento == date(2026, 12, 1)
        assert not f.data_reservada

    def test_cancelamento_sem_pagamento_nao_gera_credito(self):
        f = nova_festa()
        f.cancelar(HOJE)
        assert f.credito_retido == Decimal("0.00") and f.credito_valido_ate is None

    def test_cancelada_nao_recebe_pagamento_nem_remarcacao(self):
        f = nova_festa()
        f.cancelar(HOJE)
        with pytest.raises(TransicaoInvalidaErro):
            f.registrar_pagamento("100", HOJE)
        with pytest.raises(TransicaoInvalidaErro):
            f.remarcar(date(2027, 1, 10))

    def test_cancelamento_cancela_avisos_pendentes(self):
        f = nova_festa()
        pendente = Lembrete(date(2026, 12, 6), TipoLembrete.LEMBRETE_14_DIAS)
        enviado = Lembrete(HOJE, TipoLembrete.CONFIRMACAO)
        enviado.marcar_enviado(HOJE)
        f.adicionar_lembrete(pendente)
        f.adicionar_lembrete(enviado)
        f.cancelar(HOJE)
        assert pendente.situacao is SituacaoLembrete.CANCELADO
        assert enviado.situacao is SituacaoLembrete.ENVIADO

    def test_remarcar_altera_data_e_horario(self):
        f = nova_festa()
        f.remarcar(date(2027, 1, 10), inicio="10:00", termino="12:00")
        assert f.data == date(2027, 1, 10) and (f.inicio, f.termino) == (time(10, 0), time(12, 0))
        f.remarcar("15/01/2027")  # mantém o horário
        assert f.data == date(2027, 1, 15) and f.inicio == time(10, 0)

    def test_remarcar_com_horario_invalido_nao_altera_nada(self):
        f = nova_festa()
        with pytest.raises(ValidacaoErro):
            f.remarcar(date(2027, 1, 10), inicio="18:00")  # término 17:00 ficaria antes
        assert f.data == date(2026, 12, 20) and f.inicio == time(14, 0)


class TesteFestaEquipe:
    def test_adicionar_e_remover(self):
        f = nova_festa()
        ana, bruno = Recreador("Ana Lima", id=1), Recreador("Bruno Costa", id=2)
        f.adicionar_recreador(ana)
        f.adicionar_recreador(bruno)
        assert [r.identificacao for r in f.recreadores] == ["Ana Lima", "Bruno Costa"]
        f.remover_recreador(ana)
        assert [r.identificacao for r in f.recreadores] == ["Bruno Costa"]

    def test_duplicado_e_inexistente(self):
        f = nova_festa()
        ana = Recreador("Ana Lima", id=1)
        f.adicionar_recreador(ana)
        with pytest.raises(RegraDeNegocioErro, match="já está escalado"):
            f.adicionar_recreador(Recreador("ana lima"))
        with pytest.raises(RegraDeNegocioErro, match="não está escalado"):
            f.remover_recreador(Recreador("Zé"))
        with pytest.raises(ValidacaoErro):
            f.adicionar_recreador("Ana")  # type: ignore[arg-type]

    def test_equipe_so_muda_em_festa_confirmada(self):
        f = nova_festa()
        f.cancelar(HOJE)
        with pytest.raises(TransicaoInvalidaErro):
            f.adicionar_recreador(Recreador("Ana Lima", id=1))


class TesteFestaConsultasEPersistencia:
    def test_atividades_fora_da_faixa(self):
        f = nova_festa(
            faixa_etaria=(4, 9),
            atividades=[Atividade("Pintura facial"), Atividade("Futebol", FaixaEtaria(8, 12))],
        )
        assert [a.nome for a in f.atividades_fora_da_faixa()] == ["Futebol"]

    def test_metodos_especiais(self):
        f = nova_festa()
        assert "20/12/2026" in str(f) and "14:00–17:00" in str(f) and "Maria Souza" in str(f)
        assert "confirmada" in repr(f) and "Festa(" in repr(f)
        f.atribuir_id(5)
        assert "#5" in str(f)

    def test_ordenacao_por_data_e_horario(self):
        tarde = nova_festa(inicio="15:00", termino="18:00")
        manha = nova_festa(inicio="09:00", termino="11:00")
        outro_dia = nova_festa(data=date(2026, 12, 19))
        assert sorted([tarde, manha, outro_dia]) == [outro_dia, manha, tarde]
        assert manha < tarde

    def test_ida_e_volta_dicionario_preserva_tudo(self):
        contratante = Contratante("Maria Souza", "99981234567", id=1)
        ana = Recreador("Ana Lima", id=4)
        f = nova_festa(contratante, atividades=[Atividade("Futebol", FaixaEtaria(8, 12)), "Pintura"])
        f.atribuir_id(9)
        f.adicionar_recreador(ana)
        f.adicionar_lembrete(Lembrete(HOJE, TipoLembrete.CONFIRMACAO))
        f.registrar_pagamento("500", HOJE)
        f.cancelar(date(2026, 12, 1))

        copia = Festa.de_dicionario(f.para_dicionario(), {"contratantes": {1: contratante}, "recreadores": {4: ana}})
        assert copia.id == 9 and copia.contratante is contratante
        assert copia.recreadores == (ana,)
        assert copia.situacao is SituacaoFesta.CANCELADA
        assert copia.total_recebido == Decimal("500.00")
        assert copia.credito_retido == Decimal("500.00")
        assert copia.credito_valido_ate == date(2027, 12, 1)
        assert [str(a) for a in copia.atividades] == ["Futebol (8 a 12 anos)", "Pintura"]
        assert copia.lembretes[0].situacao is SituacaoLembrete.CANCELADO
        assert copia.para_dicionario() == f.para_dicionario()

    def test_festa_sem_contratante_gravado_nao_serializa(self):
        with pytest.raises(ValidacaoErro):
            nova_festa(Contratante("Maria Souza", "99981234567")).para_dicionario()  # contratante sem id


class TesteDimensionamento:
    """RN-06: dados reproduzidos como informado, sem extrapolar."""

    @pytest.mark.parametrize(
        "quantidade, faixa, esperado",
        [
            (10, (3, 12), (2, 2)),
            (5, (4, 9), (2, 2)),
            (20, (10, 12), (2, 3)),
            (15, (11, 12), (2, 3)),
            (50, (5, 12), (6, 7)),
            (30, (8, 11), (6, 7)),
        ],
    )
    def test_combinacoes_informadas(self, quantidade, faixa, esperado):
        assert recomendar_equipe(quantidade, FaixaEtaria(*faixa)) == esperado

    @pytest.mark.parametrize(
        "quantidade, faixa",
        [
            (51, (5, 12)),  # acima de 50 crianças
            (30, (3, 12)),  # faixa mais ampla que a informada para 50 crianças
            (10, (0, 12)),  # fora de 3 a 12 anos
        ],
    )
    def test_combinacoes_nao_cobertas_nao_sao_extrapoladas(self, quantidade, faixa):
        assert recomendar_equipe(quantidade, FaixaEtaria(*faixa)) is None

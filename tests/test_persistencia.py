import json
import os
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from conftest import DATA_FESTA, HOJE, RepositorioFalho
from docinho import Sistema
from docinho.excecoes import NaoEncontradoErro, PersistenciaErro
from docinho.modelos import SituacaoFesta, SituacaoLembrete
from docinho.persistencia import Armazenamento, RepositorioJSON, RepositorioMemoria


@pytest.fixture
def caminho(tmp_path):
    return tmp_path / "dados" / "docinho.json"


def popular(sistema):
    maria = sistema.contratantes.cadastrar("Maria Souza", "(99) 98123-4567")
    joao = sistema.contratantes.cadastrar("João Pereira", "(99) 99876-5432")
    ana = sistema.recreadores.cadastrar("Ana Lima")
    bruno = sistema.recreadores.cadastrar("Bruno Costa")
    base = dict(
        inicio="14:00", termino="17:00", endereco="Rua das Flores, 120", quantidade_criancas=8,
        faixa_etaria=(4, 9), valor_combinado="1000.00", atividades=["Pintura facial", "Caça ao tesouro"],
        deslocamento="não se aplica", data_confirmacao=HOJE,
    )
    f1 = sistema.festas.agendar(
        contratante_id=maria.id, data=DATA_FESTA, recreadores_ids=[ana.id, bruno.id], brinde=None, **base
    )
    sistema.financeiro.registrar_pagamento(f1.id, "500", HOJE)
    sistema.lembretes.marcar_enviado(f1.id, 0, HOJE)
    f2 = sistema.festas.agendar(
        contratante_id=joao.id, data=date(2027, 1, 10), recreadores_ids=[ana.id], brinde="Bolo", **base
    )
    sistema.financeiro.registrar_pagamento(f2.id, "500", HOJE)
    sistema.festas.cancelar(f2.id, date(2026, 12, 1))
    return f1, f2


class TesteRepositorioMemoria:
    def test_ida_e_volta_com_copia_independente(self):
        repo = RepositorioMemoria()
        assert repo.carregar() == {}
        dados = {"a": [1, 2]}
        repo.salvar(dados)
        dados["a"].append(3)
        assert repo.carregar() == {"a": [1, 2]}


class TesteRepositorioJSON:
    def test_arquivo_inexistente_comeca_vazio(self, caminho):
        assert RepositorioJSON(caminho).carregar() == {}

    def test_salvar_cria_pastas_e_gera_json_legivel(self, caminho):
        repo = RepositorioJSON(caminho)
        repo.salvar({"nome": "Caça ao tesouro"})
        assert caminho.exists()
        assert "Caça ao tesouro" in caminho.read_text(encoding="utf-8")
        assert repo.carregar() == {"nome": "Caça ao tesouro"}

    def test_arquivo_corrompido_gera_erro_claro(self, caminho):
        caminho.parent.mkdir(parents=True)
        caminho.write_text("{ isto não é json", encoding="utf-8")
        with pytest.raises(PersistenciaErro, match="cópia de segurança"):
            RepositorioJSON(caminho).carregar()

    def test_formato_inesperado(self, caminho):
        caminho.parent.mkdir(parents=True)
        caminho.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(PersistenciaErro, match="formato"):
            RepositorioJSON(caminho).carregar()

    def test_gravacao_atomica_preserva_arquivo_em_caso_de_falha(self, caminho, monkeypatch):
        repo = RepositorioJSON(caminho)
        repo.salvar({"versao": "boa"})

        def falhar(*args, **kwargs):
            raise OSError("falha simulada")

        monkeypatch.setattr(os, "replace", falhar)
        with pytest.raises(PersistenciaErro, match="Falha ao gravar"):
            repo.salvar({"versao": "ruim"})
        monkeypatch.undo()
        assert repo.carregar() == {"versao": "boa"}
        assert not list(caminho.parent.glob("*.tmp"))

    def test_dado_nao_serializavel_nao_corrompe_o_arquivo(self, caminho):
        repo = RepositorioJSON(caminho)
        repo.salvar({"ok": 1})
        with pytest.raises(PersistenciaErro):
            repo.salvar({"objeto": object()})
        assert repo.carregar() == {"ok": 1}


class TesteArmazenamentoEPersistenciaCompleta:
    def test_dados_sobrevivem_ao_reabrir_o_sistema(self, caminho):
        sistema = Sistema.com_arquivo(caminho)
        f1, f2 = popular(sistema)

        reaberto = Sistema.com_arquivo(caminho)
        assert [c.nome for c in reaberto.contratantes.listar()] == ["João Pereira", "Maria Souza"]
        assert [r.identificacao for r in reaberto.recreadores.listar()] == ["Ana Lima", "Bruno Costa"]
        assert len(reaberto.agenda.consultar()) == 2

        g1, g2 = reaberto.festas.obter(f1.id), reaberto.festas.obter(f2.id)
        assert g1.contratante.nome == "Maria Souza"
        assert [r.identificacao for r in g1.recreadores] == ["Ana Lima", "Bruno Costa"]
        assert g1.valor_combinado == Decimal("1000.00") and g1.saldo_pendente == Decimal("500.00")
        assert g1.pagamentos[0].saldo_pendente == Decimal("500.00")
        assert g1.detalhes.brinde == "Brinde de primeira contratação"
        assert g1.lembretes[0].situacao is SituacaoLembrete.ENVIADO
        assert g1.lembretes[0].data_envio == HOJE
        assert [a.nome for a in g1.atividades] == ["Pintura facial", "Caça ao tesouro"]
        assert g2.situacao is SituacaoFesta.CANCELADA and g2.credito_retido == Decimal("500.00")
        assert g2.credito_valido_ate == date(2027, 12, 1)
        assert g1.recreadores[0] is reaberto.recreadores.obter(1)
        assert g2.recreadores[0] is g1.recreadores[0]

    def test_identificadores_continuam_a_sequencia_apos_reabrir(self, caminho):
        sistema = Sistema.com_arquivo(caminho)
        popular(sistema)
        reaberto = Sistema.com_arquivo(caminho)
        novo = reaberto.contratantes.cadastrar("Carla Mendes", "(99) 98811-2233")
        assert novo.id == 3
        assert reaberto.recreadores.cadastrar("Camila Rocha").id == 3

    def test_arquivo_gravado_tem_estrutura_esperada(self, caminho):
        popular(Sistema.com_arquivo(caminho))
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        assert set(dados) == {"versao", "contadores", "contratantes", "recreadores", "festas"}
        assert dados["contadores"] == {"contratante": 2, "recreador": 2, "festa": 2}
        assert len(dados["festas"]) == 2 and dados["festas"][0]["pagamentos"][0]["valor_recebido"] == "500.00"

    def test_alteracoes_sao_gravadas_a_cada_operacao(self, caminho):
        sistema = Sistema.com_arquivo(caminho)
        f1, _ = popular(sistema)
        sistema.financeiro.registrar_pagamento(f1.id, "100", HOJE)
        assert Sistema.com_arquivo(caminho).festas.obter(f1.id).total_recebido == Decimal("600.00")

    def test_crud_excluir_persiste(self, caminho):
        sistema = Sistema.com_arquivo(caminho)
        c = sistema.contratantes.cadastrar("Carla Mendes", "(99) 98811-2233")
        r = sistema.recreadores.cadastrar("Felipe Nunes")
        sistema.contratantes.remover(c.id)
        sistema.recreadores.remover(r.id)
        reaberto = Sistema.com_arquivo(caminho)
        assert reaberto.contratantes.listar() == [] and reaberto.recreadores.listar() == []
        with pytest.raises(NaoEncontradoErro):
            reaberto.contratantes.obter(c.id)

    def test_repositorio_em_memoria_tambem_funciona(self):
        repo = RepositorioMemoria()
        popular(Sistema(repo))
        assert len(Armazenamento(repo).festas) == 2


class TesteTransacoes:
    def test_falha_ao_gravar_pagamento_desfaz_o_pagamento(self):
        repo = RepositorioFalho()
        sistema = Sistema(repo)
        f1, _ = popular(sistema)
        saldo_antes = sistema.armazenamento.festas[f1.id].saldo_pendente

        repo.falhar = True
        with pytest.raises(PersistenciaErro):
            sistema.financeiro.registrar_pagamento(f1.id, "500", HOJE)

        festa = sistema.armazenamento.festas[f1.id]
        assert festa.saldo_pendente == saldo_antes == Decimal("500.00")
        assert len(festa.pagamentos) == 1 and festa.situacao is SituacaoFesta.CONFIRMADA
        assert Sistema(repo).festas.obter(f1.id).saldo_pendente == Decimal("500.00")

        repo.falhar = False
        sistema.financeiro.registrar_pagamento(f1.id, "500", HOJE)
        assert sistema.festas.obter(f1.id).saldo_pendente == Decimal("0.00")

    def test_falha_ao_agendar_nao_deixa_festa_pela_metade(self, dados_festa):
        repo = RepositorioFalho()
        sistema = Sistema(repo)
        sistema.contratantes.cadastrar("Maria Souza", "(99) 98123-4567")
        for nome in ("Ana Lima", "Bruno Costa"):
            sistema.recreadores.cadastrar(nome)
        repo.falhar = True
        with pytest.raises(PersistenciaErro):
            sistema.festas.agendar(**dados_festa)
        assert len(sistema.agenda.consultar()) == 0
        repo.falhar = False
        assert sistema.festas.agendar(**dados_festa).id == 1

    def test_falha_ao_cadastrar_contratante(self):
        repo = RepositorioFalho()
        sistema = Sistema(repo)
        repo.falhar = True
        with pytest.raises(PersistenciaErro):
            sistema.contratantes.cadastrar("Maria Souza", "(99) 98123-4567")
        assert sistema.contratantes.listar() == []

    def test_erro_de_regra_nao_grava_nem_desfaz_o_que_ja_existe(self, dados_festa):
        repo = RepositorioFalho()
        sistema = Sistema(repo)
        popular(sistema)
        festa = sistema.festas.obter(1)
        from docinho.excecoes import ValidacaoErro

        with pytest.raises(ValidacaoErro):
            sistema.financeiro.registrar_pagamento(1, "9999", HOJE)
        assert sistema.festas.obter(1) is festa


class TesteBackup:
    def test_criar_backup_copia_o_arquivo(self, caminho):
        relogio = {"agora": datetime(2026, 11, 24, 10, 0, 0)}
        repo = RepositorioJSON(caminho, agora=lambda: relogio["agora"])
        repo.salvar({"x": 1})
        copia = repo.criar_backup()
        assert copia.name == "docinho_20261124_100000.json"
        assert json.loads(copia.read_text(encoding="utf-8")) == {"x": 1}

    def test_backup_sem_dados_e_erro(self, caminho):
        with pytest.raises(PersistenciaErro, match="Não há dados"):
            RepositorioJSON(caminho).criar_backup()

    def test_backup_a_cada_24_horas(self, caminho):
        relogio = {"agora": datetime(2026, 11, 24, 10, 0, 0)}
        repo = RepositorioJSON(caminho, agora=lambda: relogio["agora"])
        repo.salvar({"x": 1})
        assert repo.backup_necessario(24)
        repo.criar_backup()
        relogio["agora"] += timedelta(hours=23, minutes=59)
        assert not repo.backup_necessario(24)
        relogio["agora"] += timedelta(minutes=1)
        assert repo.backup_necessario(24)

    def test_restaurar_ultima_copia_valida(self, caminho):
        relogio = {"agora": datetime(2026, 11, 24, 10, 0, 0)}
        repo = RepositorioJSON(caminho, agora=lambda: relogio["agora"])
        sistema = Sistema(repo)
        sistema.contratantes.cadastrar("Maria Souza", "(99) 98123-4567")
        repo.criar_backup()
        relogio["agora"] += timedelta(days=1)
        sistema.contratantes.cadastrar("João Pereira", "(99) 99876-5432")
        repo.criar_backup()
        relogio["agora"] += timedelta(days=1)
        repo.criar_backup()
        copias = sorted(repo.pasta_backup.glob("docinho_*.json"))
        copias[-1].write_text("lixo", encoding="utf-8")
        caminho.write_text("arquivo atual danificado", encoding="utf-8")

        restaurada = repo.restaurar_ultimo_backup()
        assert restaurada == copias[-2]
        assert len(Sistema.com_arquivo(caminho).contratantes.listar()) == 2

    def test_restaurar_sem_copia_valida(self, caminho):
        repo = RepositorioJSON(caminho)
        with pytest.raises(PersistenciaErro, match="Nenhuma cópia"):
            repo.restaurar_ultimo_backup()
        repo.salvar({"x": 1})
        repo.criar_backup()
        repo.pasta_backup.joinpath(next(repo.pasta_backup.iterdir()).name).write_text("lixo")
        with pytest.raises(PersistenciaErro, match="Nenhuma cópia"):
            repo.restaurar_ultimo_backup()

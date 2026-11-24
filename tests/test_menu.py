import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from docinho import Sistema
from docinho.menu import principal

RAIZ = Path(__file__).resolve().parent.parent


def data_futura(dias=30):
    return (date.today() + timedelta(days=dias)).strftime("%d/%m/%Y")


def executar(caminho, roteiro):
    respostas = iter(roteiro)
    exibido = []

    def entrada(pergunta):
        exibido.append(pergunta)
        try:
            return next(respostas)
        except StopIteration:
            raise EOFError from None

    codigo = principal(["--dados", str(caminho)], entrada, exibido.append)
    return codigo, "\n".join(exibido)


def cadastros(*nomes_recreadores):
    roteiro = ["1", "Maria Souza", "(99) 98123-4567", "1", "João Pereira", "(99) 99876-5432"]
    for nome in nomes_recreadores:
        roteiro += ["3", nome]
    return roteiro


def agendar(contratante, data, inicio, termino, recreadores, brinde="", deslocamento="não se aplica"):
    return [
        "6", str(contratante), data, inicio, termino, "Rua A, 10", "8", "4-9", "1000,00",
        "Pintura, Caça ao tesouro", recreadores, brinde, deslocamento,
    ]


@pytest.fixture
def caminho(tmp_path):
    return tmp_path / "docinho.json"


class TesteMenu:
    def test_cadastrar_e_buscar_contratante(self, caminho):
        codigo, saida = executar(
            caminho, ["1", "Maria Souza", "(99) 98123-4567", "2", "maria", "2", "981234567", "2", "zzz", "0"]
        )
        assert codigo == 0
        assert "Contratante cadastrado: #1" in saida
        assert saida.count("#1 — Maria Souza — (99) 98123-4567") >= 3
        assert "Nenhum contratante encontrado." in saida
        assert "Até logo!" in saida
        assert len(Sistema.com_arquivo(caminho).contratantes.listar()) == 1

    def test_erros_aparecem_em_portugues_e_o_menu_continua(self, caminho):
        _, saida = executar(caminho, ["1", "Maria", "123", "1", "", "0"])
        assert "Erro: Telefone inválido" in saida
        assert "Erro: O campo 'Nome' é obrigatório." in saida
        assert "Até logo!" in saida

    def test_opcao_invalida(self, caminho):
        _, saida = executar(caminho, ["99", "abc", "", "0"])
        assert saida.count("Opção inválida.") == 3

    def test_fim_da_entrada_encerra_sem_erro(self, caminho):
        codigo, _ = executar(caminho, [])
        assert codigo == 0

    def test_numero_invalido_gera_erro_amigavel(self, caminho):
        _, saida = executar(caminho, ["8", "abc", "0"])
        assert "Erro: O campo 'Número da festa' precisa ser um número inteiro." in saida

    def test_disponibilidade_de_recreador(self, caminho):
        _, saida = executar(caminho, ["3", "Ana Lima", "5", "1", "n", "4", "0"])
        assert "Atualizado: Ana Lima (indisponível)" in saida


class TesteFluxoCompleto:
    def test_agendar_resumo_pagamento_financeiro_e_avisos(self, caminho):
        roteiro = (
            cadastros("Ana Lima", "Bruno Costa")[:3]
            + ["3", "Ana Lima", "3", "Bruno Costa"]
            + agendar(1, data_futura(30), "14:00", "17:00", "1,2")
            + ["8", "1"]
            + ["10", "1", "500,00"]
            + ["15"]
            + ["7", ""]
            + ["11", "1", "11", "0"]
        )
        codigo, saida = executar(caminho, roteiro)
        assert codigo == 0
        assert "Festa registrada: Festa #1" in saida
        assert "Brinde de primeira contratação" in saida
        assert "Entrada prevista: R$ 500,00" in saida
        assert "=== FESTA #1 — CONFIRMADA ===" in saida
        assert "Pintura facial" not in saida and "Pintura" in saida
        assert "Registrado: " in saida and "Saldo pendente: R$ 500,00 — situação: confirmada" in saida
        assert "Maria Souza: contratado R$ 1.000,00 | recebido R$ 500,00 | a receber R$ 500,00" in saida
        assert "Total a receber: R$ 500,00" in saida
        assert "O envio é manual, pelo WhatsApp" in saida
        assert "Aviso marcado como enviado." in saida
        assert "Nenhum aviso pendente para hoje." in saida
        assert "[confirmada]" in saida

    def test_alerta_de_escala_com_confirmacao_da_gestora(self, caminho):
        data = data_futura(30)
        roteiro = (
            cadastros("Ana Lima", "Bruno Costa")
            + agendar(1, data, "14:00", "17:00", "1,2")
            + agendar(2, data, "15:00", "18:00", "1")
            + ["n"]
            + agendar(2, data, "15:00", "18:00", "1")
            + ["s"]
            + ["0"]
        )
        _, saida = executar(caminho, roteiro)
        assert saida.count("ALERTA DE ESCALA:") == 2
        assert "Ana Lima já está em outra festa no mesmo horário" in saida
        assert "Festa não registrada. Ajuste a escala e tente novamente." in saida
        assert "Festa registrada: Festa #2" in saida
        assert len(Sistema.com_arquivo(caminho).agenda.consultar()) == 2

    def test_alocar_recreador_com_alerta(self, caminho):
        data = data_futura(30)
        roteiro = (
            cadastros("Ana Lima", "Bruno Costa")
            + agendar(1, data, "14:00", "17:00", "1")
            + agendar(2, data, "15:00", "18:00", "2")
            + ["9", "2", "1", "n"]
            + ["9", "2", "1", "s"]
            + ["9", "1", "2"]
            + ["s", "0"]
        )
        _, saida = executar(caminho, roteiro)
        assert "Alocação cancelada." in saida
        assert saida.count("Recreador escalado.") == 2

    def test_remarcar_refaz_avisos(self, caminho):
        nova = data_futura(60)
        roteiro = (
            cadastros("Ana Lima")[:3]
            + ["3", "Ana Lima"]
            + agendar(1, data_futura(30), "14:00", "17:00", "1")
            + ["12", "1", nova, "", ""]
            + ["0"]
        )
        _, saida = executar(caminho, roteiro)
        assert "Remarcada: Festa #1" in saida and "Avisos refeitos" in saida
        festa = Sistema.com_arquivo(caminho).festas.obter(1)
        assert festa.data.strftime("%d/%m/%Y") == nova
        assert len(festa.lembretes) == 5

    def test_cancelar_com_e_sem_confirmacao(self, caminho):
        roteiro = (
            cadastros("Ana Lima")[:3]
            + ["3", "Ana Lima"]
            + agendar(1, data_futura(30), "14:00", "17:00", "1")
            + ["10", "1", "500,00"]
            + ["14", "1", "n"]
            + ["14", "1", "s"]
            + ["15", "0"]
        )
        _, saida = executar(caminho, roteiro)
        assert "Cancelamento não realizado." in saida
        assert "Cancelada. Crédito retido de R$ 500,00 válido até" in saida
        assert "Crédito retido — Festa #1" in saida

    def test_marcar_realizada_futura_e_recusada(self, caminho):
        roteiro = (
            cadastros("Ana Lima")[:3]
            + ["3", "Ana Lima"]
            + agendar(1, data_futura(30), "14:00", "17:00", "1")
            + ["13", "1", "0"]
        )
        _, saida = executar(caminho, roteiro)
        assert "Erro: Não é possível marcar como realizada uma festa com data futura." in saida

    def test_campo_obrigatorio_vazio_na_festa(self, caminho):
        roteiro = cadastros("Ana Lima")[:3] + ["3", "Ana Lima"]
        roteiro += agendar(1, data_futura(30), "14:00", "17:00", "1", deslocamento="")
        roteiro += ["0"]
        _, saida = executar(caminho, roteiro)
        assert "Erro: Campos obrigatórios não preenchidos: deslocamento." in saida
        assert len(Sistema.com_arquivo(caminho).agenda.consultar()) == 0


class TesteBackupEArquivo:
    def test_backup_manual_e_automatico(self, caminho):
        executar(caminho, ["1", "Maria Souza", "(99) 98123-4567", "16", "0"])
        assert list((caminho.parent / "backups").glob("docinho_*.json"))
        pasta = caminho.parent / "backups"
        for arquivo in pasta.iterdir():
            arquivo.unlink()
        executar(caminho, ["0"])
        assert len(list(pasta.glob("docinho_*.json"))) == 1
        executar(caminho, ["0"])
        assert len(list(pasta.glob("docinho_*.json"))) == 1

    def test_arquivo_corrompido_retorna_erro(self, caminho):
        caminho.write_text("lixo", encoding="utf-8")
        codigo, saida = executar(caminho, ["0"])
        assert codigo == 1 and "Erro ao abrir os dados" in saida


class TesteSeed:
    def test_script_de_carga_inicial(self, tmp_path):
        destino = tmp_path / "docinho.json"
        comando = [sys.executable, str(RAIZ / "scripts" / "carga_inicial.py"), "--dados", str(destino)]
        resultado = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8")
        assert resultado.returncode == 0, resultado.stdout + resultado.stderr
        assert "Carga inicial concluída." in resultado.stdout

        sistema = Sistema.com_arquivo(destino)
        assert len(sistema.recreadores.listar()) == 6
        assert len(sistema.contratantes.listar()) == 3
        assert len(sistema.agenda.consultar()) == 3

        repetido = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8")
        assert repetido.returncode == 1 and "--forcar" in repetido.stdout
        forcado = subprocess.run(comando + ["--forcar"], capture_output=True, text=True, encoding="utf-8")
        assert forcado.returncode == 0

from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path
from typing import Callable, List, Optional

from .excecoes import ConflitoEscalaErro, DocinhoErro, ValidacaoErro
from .modelos import SituacaoFesta
from .persistencia import RepositorioJSON
from .sistema import Sistema
from .validacao import moeda, para_data


class Interface:
    def __init__(
        self,
        sistema: Sistema,
        entrada: Callable[[str], str] = input,
        saida: Callable[[str], None] = print,
    ):
        self.sistema = sistema
        self._entrada = entrada
        self._saida = saida
        self._opcoes = [
            ("Cadastrar contratante", self.cadastrar_contratante),
            ("Buscar contratante (nome ou telefone)", self.buscar_contratante),
            ("Cadastrar recreador", self.cadastrar_recreador),
            ("Listar recreadores", self.listar_recreadores),
            ("Alterar disponibilidade de recreador", self.alterar_disponibilidade),
            ("Agendar festa", self.agendar_festa),
            ("Agenda de festas", self.mostrar_agenda),
            ("Resumo da festa", self.resumo_festa),
            ("Alocar recreador em festa", self.alocar_recreador),
            ("Registrar pagamento", self.registrar_pagamento),
            ("Avisos pendentes", self.avisos_pendentes),
            ("Remarcar festa", self.remarcar_festa),
            ("Marcar festa como realizada", self.marcar_realizada),
            ("Cancelar festa", self.cancelar_festa),
            ("Financeiro (a receber e créditos)", self.mostrar_financeiro),
            ("Criar cópia de segurança agora", self.criar_backup),
        ]

    def _dizer(self, texto: str = "") -> None:
        self._saida(texto)

    def _pedir(self, rotulo: str, obrigatorio: bool = True) -> str:
        resposta = self._entrada(f"{rotulo}: ").strip()
        if obrigatorio and not resposta:
            raise ValidacaoErro(f"O campo '{rotulo}' é obrigatório.")
        return resposta

    def _pedir_inteiro(self, rotulo: str) -> int:
        texto = self._pedir(rotulo)
        try:
            return int(texto)
        except ValueError:
            raise ValidacaoErro(f"O campo '{rotulo}' precisa ser um número inteiro.") from None

    def _pedir_lista_inteiros(self, rotulo: str) -> List[int]:
        texto = self._pedir(rotulo)
        try:
            return [int(parte) for parte in texto.replace(";", ",").split(",") if parte.strip()]
        except ValueError:
            raise ValidacaoErro(f"O campo '{rotulo}' precisa ter números separados por vírgula.") from None

    def _confirmar(self, pergunta: str) -> bool:
        return self._entrada(f"{pergunta} (s/n): ").strip().lower() in ("s", "sim")

    def executar(self) -> None:
        self._backup_automatico()
        self._dizer("=== Docinho Recreação Infantil — Agendamento de Festas ===")
        while True:
            self._dizer()
            for numero, (rotulo, _) in enumerate(self._opcoes, start=1):
                self._dizer(f"{numero:2d}) {rotulo}")
            self._dizer(" 0) Sair")
            try:
                escolha = self._entrada("Escolha uma opção: ").strip()
            except EOFError:
                break
            if escolha == "0":
                self._dizer("Até logo!")
                break
            if not escolha.isdigit() or not 1 <= int(escolha) <= len(self._opcoes):
                self._dizer("Opção inválida.")
                continue
            try:
                self._opcoes[int(escolha) - 1][1]()
            except ConflitoEscalaErro as alerta:
                self._dizer(f"Alerta: {alerta}")
            except DocinhoErro as erro:
                self._dizer(f"Erro: {erro}")
            except EOFError:
                break

    def _backup_automatico(self) -> None:
        repositorio = self.sistema.repositorio
        if isinstance(repositorio, RepositorioJSON) and repositorio.caminho.exists():
            try:
                if repositorio.backup_necessario(24):
                    repositorio.criar_backup()
            except DocinhoErro as erro:
                self._dizer(f"Aviso: não foi possível criar a cópia de segurança ({erro}).")

    def cadastrar_contratante(self) -> None:
        contratante = self.sistema.contratantes.cadastrar(self._pedir("Nome"), self._pedir("Telefone (com DDD)"))
        self._dizer(f"Contratante cadastrado: #{contratante.id} — {contratante}")

    def buscar_contratante(self) -> None:
        encontrados = self.sistema.contratantes.buscar(self._pedir("Nome ou telefone"))
        if not encontrados:
            self._dizer("Nenhum contratante encontrado.")
        for contratante in encontrados:
            self._dizer(f"#{contratante.id} — {contratante}")

    def cadastrar_recreador(self) -> None:
        recreador = self.sistema.recreadores.cadastrar(self._pedir("Identificação (nome)"))
        self._dizer(f"Recreador cadastrado: #{recreador.id} — {recreador}")

    def listar_recreadores(self) -> None:
        recreadores = self.sistema.recreadores.listar()
        if not recreadores:
            self._dizer("Nenhum recreador cadastrado.")
        for recreador in recreadores:
            self._dizer(f"#{recreador.id} — {recreador}")

    def alterar_disponibilidade(self) -> None:
        self.listar_recreadores()
        recreador_id = self._pedir_inteiro("Número do recreador")
        disponivel = self._confirmar("Está disponível para a escala?")
        recreador = self.sistema.recreadores.definir_disponibilidade(recreador_id, disponivel)
        self._dizer(f"Atualizado: {recreador}")

    def agendar_festa(self) -> None:
        self._dizer("Contratantes cadastrados:")
        for contratante in self.sistema.contratantes.listar():
            self._dizer(f"  #{contratante.id} — {contratante}")
        self._dizer("Recreadores:")
        for recreador in self.sistema.recreadores.listar():
            self._dizer(f"  #{recreador.id} — {recreador}")
        dados = dict(
            contratante_id=self._pedir_inteiro("Número do contratante"),
            data=self._pedir("Data da festa (DD/MM/AAAA)"),
            inicio=self._pedir("Horário de início (HH:MM)"),
            termino=self._pedir("Horário de término (HH:MM)"),
            endereco=self._pedir("Endereço"),
            quantidade_criancas=self._pedir_inteiro("Quantidade de crianças"),
            faixa_etaria=self._pedir("Faixa etária (ex.: 5-9)"),
            valor_combinado=self._pedir("Valor combinado (ex.: 1000,00)"),
            atividades=[a.strip() for a in self._pedir("Brincadeiras previstas (separe por vírgula)").split(",") if a.strip()],
            recreadores_ids=self._pedir_lista_inteiros("Recreadores escalados (números separados por vírgula)"),
            brinde=self._pedir("Benefícios/brindes (ou 'não se aplica')", obrigatorio=False),
            deslocamento=self._pedir("Deslocamento / outra cidade (ou 'não se aplica')", obrigatorio=False),
        )
        try:
            festa = self.sistema.festas.agendar(**dados)
        except ConflitoEscalaErro as alerta:
            self._dizer("ALERTA DE ESCALA:")
            for conflito in alerta.conflitos:
                self._dizer(f"  ! {conflito}")
            if not self._confirmar("Manter esta escala mesmo assim?"):
                self._dizer("Festa não registrada. Ajuste a escala e tente novamente.")
                return
            festa = self.sistema.festas.agendar(**dados, forcar_escala=True)
        self._dizer(f"Festa registrada: {festa}")
        if festa.detalhes.brinde:
            self._dizer(f"  {festa.detalhes}")
        self._dizer(f"  Entrada prevista: {moeda(festa.entrada_prevista)} — a data só fica reservada após o pagamento da entrada.")

    def mostrar_agenda(self) -> None:
        inicial = self._pedir("A partir de (DD/MM/AAAA, Enter para todas)", obrigatorio=False)
        agenda = self.sistema.agenda.consultar(data_inicial=inicial or None)
        if not len(agenda):
            self._dizer("Nenhuma festa na agenda.")
        for festa in agenda:
            self._dizer(str(festa))

    def resumo_festa(self) -> None:
        self._dizer(str(self.sistema.resumos.gerar(self._pedir_inteiro("Número da festa"))))

    def alocar_recreador(self) -> None:
        festa_id = self._pedir_inteiro("Número da festa")
        recreador_id = self._pedir_inteiro("Número do recreador")
        try:
            self.sistema.escala.alocar(festa_id, recreador_id)
        except ConflitoEscalaErro as alerta:
            self._dizer("ALERTA DE ESCALA:")
            for conflito in alerta.conflitos:
                self._dizer(f"  ! {conflito}")
            if not self._confirmar("Escalar mesmo assim?"):
                self._dizer("Alocação cancelada.")
                return
            self.sistema.escala.alocar(festa_id, recreador_id, forcar=True)
        self._dizer("Recreador escalado.")

    def registrar_pagamento(self) -> None:
        festa_id = self._pedir_inteiro("Número da festa")
        valor = self._pedir("Valor recebido (ex.: 500,00)")
        pagamento = self.sistema.financeiro.registrar_pagamento(festa_id, valor, date.today())
        festa = self.sistema.festas.obter(festa_id)
        self._dizer(f"Registrado: {pagamento}")
        self._dizer(f"Saldo pendente: {moeda(festa.saldo_pendente)} — situação: {festa.situacao.value}")

    def avisos_pendentes(self) -> None:
        avisos = self.sistema.lembretes.avisos_pendentes(date.today())
        if not avisos:
            self._dizer("Nenhum aviso pendente para hoje.")
            return
        for numero, aviso in enumerate(avisos, start=1):
            self._dizer(f"{numero}) {aviso}")
        self._dizer("O envio é manual, pelo WhatsApp. O sistema não envia mensagens.")
        escolha = self._pedir("Número do aviso já enviado (Enter para voltar)", obrigatorio=False)
        if escolha.isdigit() and 1 <= int(escolha) <= len(avisos):
            aviso = avisos[int(escolha) - 1]
            self.sistema.lembretes.marcar_enviado(aviso.festa.id, aviso.indice, date.today())
            self._dizer("Aviso marcado como enviado.")

    def remarcar_festa(self) -> None:
        festa_id = self._pedir_inteiro("Número da festa")
        nova_data = self._pedir("Nova data (DD/MM/AAAA)")
        inicio = self._pedir("Novo horário de início (Enter para manter)", obrigatorio=False) or None
        termino = self._pedir("Novo horário de término (Enter para manter)", obrigatorio=False) or None
        try:
            festa = self.sistema.festas.remarcar(festa_id, nova_data, inicio, termino)
        except ConflitoEscalaErro as alerta:
            self._dizer("ALERTA DE ESCALA:")
            for conflito in alerta.conflitos:
                self._dizer(f"  ! {conflito}")
            if not self._confirmar("Remarcar mesmo assim?"):
                self._dizer("Remarcação cancelada.")
                return
            festa = self.sistema.festas.remarcar(festa_id, nova_data, inicio, termino, forcar_escala=True)
        self._dizer(f"Remarcada: {festa}. Avisos refeitos a partir de hoje.")

    def marcar_realizada(self) -> None:
        festa = self.sistema.festas.marcar_realizada(self._pedir_inteiro("Número da festa"))
        self._dizer(f"Atualizada: {festa}. Saldo pendente: {moeda(festa.saldo_pendente)}")

    def cancelar_festa(self) -> None:
        festa_id = self._pedir_inteiro("Número da festa")
        if not self._confirmar("Confirmar o cancelamento? O valor pago fica retido por 1 ano"):
            self._dizer("Cancelamento não realizado.")
            return
        festa = self.sistema.festas.cancelar(festa_id)
        if festa.credito_retido > 0:
            self._dizer(f"Cancelada. Crédito retido de {moeda(festa.credito_retido)} válido até {festa.credito_valido_ate:%d/%m/%Y}.")
        else:
            self._dizer("Cancelada. Não havia valor pago para reter.")

    def mostrar_financeiro(self) -> None:
        situacoes = self.sistema.financeiro.situacao_por_contratante()
        if not situacoes:
            self._dizer("Nenhuma festa com valores registrados.")
        for situacao in situacoes:
            self._dizer(str(situacao))
        self._dizer(f"Total a receber: {moeda(self.sistema.financeiro.total_a_receber())}")
        for credito in self.sistema.financeiro.creditos_retidos(date.today()):
            self._dizer(f"Crédito retido — {credito}")

    def criar_backup(self) -> None:
        repositorio = self.sistema.repositorio
        if not isinstance(repositorio, RepositorioJSON):
            self._dizer("Os dados estão apenas em memória; não há arquivo para copiar.")
            return
        self._dizer(f"Cópia criada em: {repositorio.criar_backup()}")


def _caminho_padrao() -> Path:
    return Path(os.environ.get("DOCINHO_DADOS") or Path.cwd() / "dados" / "docinho.json")


def principal(
    argv: Optional[List[str]] = None,
    entrada: Callable[[str], str] = input,
    saida: Callable[[str], None] = print,
) -> int:
    analisador = argparse.ArgumentParser(
        prog="docinho", description="Sistema de Agendamento de Festas — Docinho Recreação Infantil"
    )
    analisador.add_argument(
        "--dados",
        default=str(_caminho_padrao()),
        help="arquivo JSON com os dados (padrão: dados/docinho.json ou variável DOCINHO_DADOS)",
    )
    argumentos = analisador.parse_args(argv)
    try:
        sistema = Sistema.com_arquivo(argumentos.dados)
    except DocinhoErro as erro:
        saida(f"Erro ao abrir os dados: {erro}")
        return 1
    Interface(sistema, entrada, saida).executar()
    return 0

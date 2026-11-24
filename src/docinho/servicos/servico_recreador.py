"""Cadastro de recreadores e disponibilidade (RF-04)."""

from __future__ import annotations

from typing import List, Optional

from ..excecoes import RegraDeNegocioErro
from ..modelos import Recreador
from ..persistencia import Armazenamento
from ..validacao import sem_acentos


class ServicoRecreador:
    def __init__(self, armazenamento: Armazenamento):
        self._arm = armazenamento

    def cadastrar(self, identificacao: str, disponivel: bool = True) -> Recreador:
        novo = Recreador(identificacao, disponivel)
        if any(r == novo for r in self._arm.recreadores.values()):
            raise RegraDeNegocioErro("Já existe um recreador com esta identificação.")
        with self._arm.transacao():
            self._arm.adicionar_recreador(novo)
        return novo

    def obter(self, recreador_id: int) -> Recreador:
        return self._arm.obter_recreador(recreador_id)

    def listar(self, apenas_disponiveis: bool = False) -> List[Recreador]:
        itens = [r for r in self._arm.recreadores.values() if r.disponibilidade or not apenas_disponiveis]
        return sorted(itens, key=lambda r: sem_acentos(r.identificacao))

    def definir_disponibilidade(self, recreador_id: int, disponivel: bool) -> Recreador:
        recreador = self._arm.obter_recreador(recreador_id)
        with self._arm.transacao():
            recreador.disponibilidade = disponivel
        return recreador

    def atualizar(self, recreador_id: int, identificacao: Optional[str] = None) -> Recreador:
        recreador = self._arm.obter_recreador(recreador_id)
        if identificacao is not None:
            teste = Recreador(identificacao)
            for outro in self._arm.recreadores.values():
                if outro.id != recreador.id and outro == teste:
                    raise RegraDeNegocioErro("Já existe um recreador com esta identificação.")
            with self._arm.transacao():
                recreador.identificacao = teste.identificacao
        return recreador

    def remover(self, recreador_id: int) -> None:
        """Não exclui recreador que consta em alguma festa (o histórico depende
        dele); nesse caso, basta marcá-lo como indisponível."""
        recreador = self._arm.obter_recreador(recreador_id)
        for festa in self._arm.festas.values():
            if recreador in festa.recreadores:
                raise RegraDeNegocioErro(
                    f"{recreador.identificacao} consta na festa #{festa.id} e não pode ser excluído(a). "
                    "Marque-o(a) como indisponível."
                )
        with self._arm.transacao():
            del self._arm.recreadores[recreador.id]

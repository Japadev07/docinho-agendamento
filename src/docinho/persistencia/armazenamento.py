"""Armazenamento: coleções em memória + persistência através de um Repositório."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Dict, Iterator

from ..excecoes import DocinhoErro, NaoEncontradoErro, PersistenciaErro
from ..modelos import Contratante, EntidadeBase, Festa, Recreador
from .repositorio import Repositorio

VERSAO_DADOS = 1


class Armazenamento:
    def __init__(self, repositorio: Repositorio):
        self._repositorio = repositorio
        self._contadores = {"contratante": 0, "recreador": 0, "festa": 0}
        self.contratantes: Dict[int, Contratante] = {}
        self.recreadores: Dict[int, Recreador] = {}
        self.festas: Dict[int, Festa] = {}
        self.carregar()

    def _proximo_id(self, tipo: str) -> int:
        self._contadores[tipo] += 1
        return self._contadores[tipo]

    def adicionar_contratante(self, contratante: Contratante) -> Contratante:
        contratante.atribuir_id(self._proximo_id("contratante"))
        self.contratantes[contratante.id] = contratante
        return contratante

    def adicionar_recreador(self, recreador: Recreador) -> Recreador:
        recreador.atribuir_id(self._proximo_id("recreador"))
        self.recreadores[recreador.id] = recreador
        return recreador

    def adicionar_festa(self, festa: Festa) -> Festa:
        festa.atribuir_id(self._proximo_id("festa"))
        self.festas[festa.id] = festa
        return festa

    def obter_contratante(self, id: int) -> Contratante:
        return self._obter(self.contratantes, id, "Contratante")

    def obter_recreador(self, id: int) -> Recreador:
        return self._obter(self.recreadores, id, "Recreador")

    def obter_festa(self, id: int) -> Festa:
        return self._obter(self.festas, id, "Festa")

    @staticmethod
    def _obter(colecao: Dict[int, EntidadeBase], id: int, rotulo: str):
        try:
            return colecao[id]
        except KeyError:
            raise NaoEncontradoErro(f"{rotulo} {id} não encontrado(a).") from None

    def _serializar(self) -> dict:
        return {
            "versao": VERSAO_DADOS,
            "contadores": dict(self._contadores),
            "contratantes": [c.para_dicionario() for c in self.contratantes.values()],
            "recreadores": [r.para_dicionario() for r in self.recreadores.values()],
            "festas": [f.para_dicionario() for f in self.festas.values()],
        }

    def _popular(self, dados: dict) -> None:
        contadores = dados.get("contadores", {})
        self.contratantes = {}
        self.recreadores = {}
        self.festas = {}
        for item in dados.get("contratantes", []):
            contratante = Contratante.de_dicionario(item)
            self.contratantes[contratante.id] = contratante
        for item in dados.get("recreadores", []):
            recreador = Recreador.de_dicionario(item)
            self.recreadores[recreador.id] = recreador
        contexto = {"contratantes": self.contratantes, "recreadores": self.recreadores}
        for item in dados.get("festas", []):
            festa = Festa.de_dicionario(item, contexto)
            self.festas[festa.id] = festa
        self._contadores = {
            "contratante": max([contadores.get("contratante", 0), *self.contratantes], default=0),
            "recreador": max([contadores.get("recreador", 0), *self.recreadores], default=0),
            "festa": max([contadores.get("festa", 0), *self.festas], default=0),
        }

    def carregar(self) -> None:
        """Lê os dados do repositório (recomeça vazio se não houver nada salvo)."""
        dados = self._repositorio.carregar()
        self._popular(dados or {})

    def salvar(self) -> None:
        self._repositorio.salvar(self._serializar())

    @contextmanager
    def transacao(self) -> Iterator[None]:
        """Executa alterações e grava; se a gravação falhar, desfaz tudo."""
        instantaneo = self._serializar()
        try:
            yield
            self.salvar()
        except DocinhoErro as erro:
            if isinstance(erro, PersistenciaErro):
                self._restaurar(instantaneo)
            raise
        except Exception:
            self._restaurar(instantaneo)
            raise

    def _restaurar(self, instantaneo: dict) -> None:
        self._popular(instantaneo)
        self._contadores = dict(instantaneo["contadores"])

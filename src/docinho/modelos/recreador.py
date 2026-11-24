"""Classe Recreador (UML: identificação, disponibilidade) — RF-04."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from ..validacao import sem_acentos, texto_obrigatorio
from .base import EntidadeBase


class Recreador(EntidadeBase):
    """Profissional escalado para realizar as atividades."""

    def __init__(self, identificacao: str, disponivel: bool = True, id: Optional[int] = None):
        super().__init__(id)
        self.identificacao = identificacao
        self.disponibilidade = disponivel

    @property
    def identificacao(self) -> str:
        return self._identificacao

    @identificacao.setter
    def identificacao(self, valor: str) -> None:
        self._identificacao = texto_obrigatorio(valor, "identificação do recreador")

    @property
    def disponibilidade(self) -> bool:
        """Bruna mantém a disponibilidade atualizada (premissa da SRS)."""
        return self._disponibilidade

    @disponibilidade.setter
    def disponibilidade(self, valor: bool) -> None:
        if not isinstance(valor, bool):
            from ..excecoes import ValidacaoErro

            raise ValidacaoErro("A disponibilidade deve ser verdadeira ou falsa.")
        self._disponibilidade = valor

    def para_dicionario(self) -> dict:
        return {
            "id": self.id,
            "identificacao": self._identificacao,
            "disponibilidade": self._disponibilidade,
        }

    @classmethod
    def de_dicionario(cls, dados: Mapping[str, Any], contexto: Optional[Mapping[str, Any]] = None):
        return cls(dados["identificacao"], dados.get("disponibilidade", True), id=dados.get("id"))

    def __str__(self) -> str:
        situacao = "disponível" if self._disponibilidade else "indisponível"
        return f"{self._identificacao} ({situacao})"

    def __repr__(self) -> str:
        return (
            f"Recreador(id={self.id!r}, identificacao={self._identificacao!r}, "
            f"disponivel={self._disponibilidade!r})"
        )

    def __eq__(self, outro) -> bool:
        """Dois recreadores são o mesmo quando têm a mesma identificação."""
        if not isinstance(outro, Recreador):
            return NotImplemented
        return sem_acentos(self._identificacao) == sem_acentos(outro._identificacao)

    __hash__ = None  # type: ignore[assignment]

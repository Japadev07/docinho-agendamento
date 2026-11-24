"""Classe abstrata base das entidades persistíveis (abstração)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional


class EntidadeBase(ABC):
    """Contrato comum das entidades do sistema.

    Reúne o que Contratante, Recreador e Festa têm em comum: um identificador
    atribuído pelo armazenamento e a conversão de/para dicionário usada na
    persistência. Cada subclasse define como se descreve (``__str__``) e como
    se serializa, o que caracteriza o polimorfismo.
    """

    def __init__(self, id: Optional[int] = None):
        self._id = id

    @property
    def id(self) -> Optional[int]:
        return self._id

    def atribuir_id(self, novo_id: int) -> None:
        """O identificador é definido uma única vez, pelo armazenamento."""
        if self._id is not None and self._id != novo_id:
            raise ValueError("A entidade já possui identificador.")
        self._id = novo_id

    @abstractmethod
    def para_dicionario(self) -> dict:
        """Representação simples (JSON) da entidade."""

    @classmethod
    @abstractmethod
    def de_dicionario(cls, dados: Mapping[str, Any], contexto: Optional[Mapping[str, Any]] = None):
        """Reconstrói a entidade a partir de ``para_dicionario``."""

    @abstractmethod
    def __str__(self) -> str:
        """Descrição legível para a gestora."""

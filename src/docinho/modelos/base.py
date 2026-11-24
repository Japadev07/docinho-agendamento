from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional


class EntidadeBase(ABC):
    def __init__(self, id: Optional[int] = None):
        self._id = id

    @property
    def id(self) -> Optional[int]:
        return self._id

    def atribuir_id(self, novo_id: int) -> None:
        if self._id is not None and self._id != novo_id:
            raise ValueError("A entidade já possui identificador.")
        self._id = novo_id

    @abstractmethod
    def para_dicionario(self) -> dict:
        pass

    @classmethod
    @abstractmethod
    def de_dicionario(cls, dados: Mapping[str, Any], contexto: Optional[Mapping[str, Any]] = None):
        pass

    @abstractmethod
    def __str__(self) -> str:
        pass

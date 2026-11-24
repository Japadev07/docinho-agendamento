from __future__ import annotations

from typing import Any, Mapping, Optional

from ..validacao import formatar_telefone, normalizar_telefone, texto_obrigatorio
from .base import EntidadeBase


class Contratante(EntidadeBase):
    def __init__(self, nome: str, telefone: str, id: Optional[int] = None):
        super().__init__(id)
        self.nome = nome
        self.telefone = telefone

    @property
    def nome(self) -> str:
        return self._nome

    @nome.setter
    def nome(self, valor: str) -> None:
        nome = texto_obrigatorio(valor, "nome")
        if len(nome) < 2:
            from ..excecoes import ValidacaoErro

            raise ValidacaoErro("O nome do contratante precisa ter ao menos 2 caracteres.")
        self._nome = nome

    @property
    def telefone(self) -> str:
        return self._telefone

    @telefone.setter
    def telefone(self, valor: str) -> None:
        self._telefone = normalizar_telefone(valor)

    @property
    def telefone_formatado(self) -> str:
        return formatar_telefone(self._telefone)

    def para_dicionario(self) -> dict:
        return {"id": self.id, "nome": self._nome, "telefone": self._telefone}

    @classmethod
    def de_dicionario(cls, dados: Mapping[str, Any], contexto: Optional[Mapping[str, Any]] = None):
        return cls(dados["nome"], dados["telefone"], id=dados.get("id"))

    def __str__(self) -> str:
        return f"{self._nome} — {self.telefone_formatado}"

    def __repr__(self) -> str:
        return f"Contratante(id={self.id!r}, nome={self._nome!r}, telefone={self._telefone!r})"

    def __eq__(self, outro) -> bool:
        if not isinstance(outro, Contratante):
            return NotImplemented
        return self._telefone == outro._telefone

    __hash__ = None

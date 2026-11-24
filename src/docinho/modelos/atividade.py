"""Brincadeira/atividade prevista para a festa (RF-05, RN-01)."""

from __future__ import annotations

from typing import Optional

from ..validacao import texto_obrigatorio
from .faixa_etaria import FaixaEtaria


class Atividade:
    """Brincadeira com indicação etária opcional."""

    def __init__(self, nome: str, indicacao: Optional[FaixaEtaria] = None):
        self._nome = texto_obrigatorio(nome, "atividade")
        self._indicacao = FaixaEtaria.de(indicacao) if indicacao is not None else None

    @property
    def nome(self) -> str:
        return self._nome

    @property
    def indicacao(self) -> Optional[FaixaEtaria]:
        return self._indicacao

    def adequada_para(self, faixa: FaixaEtaria) -> bool:
        """Sem indicação etária, a atividade é considerada adequada."""
        return self._indicacao is None or self._indicacao.cobre(faixa)

    @classmethod
    def de(cls, valor) -> "Atividade":
        """Aceita Atividade ou apenas o nome (texto)."""
        return valor if isinstance(valor, cls) else cls(valor)

    def para_dicionario(self) -> dict:
        return {
            "nome": self._nome,
            "indicacao": self._indicacao.para_dicionario() if self._indicacao else None,
        }

    @classmethod
    def de_dicionario(cls, dados) -> "Atividade":
        indicacao = dados.get("indicacao")
        return cls(dados["nome"], FaixaEtaria.de(indicacao) if indicacao else None)

    def __eq__(self, outra) -> bool:
        if not isinstance(outra, Atividade):
            return NotImplemented
        return (self._nome.casefold(), self._indicacao) == (outra._nome.casefold(), outra._indicacao)

    def __hash__(self) -> int:
        return hash((self._nome.casefold(), self._indicacao))

    def __str__(self) -> str:
        if self._indicacao:
            return f"{self._nome} ({self._indicacao})"
        return self._nome

    def __repr__(self) -> str:
        return f"Atividade({self._nome!r}, {self._indicacao!r})"

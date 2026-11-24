from __future__ import annotations

from typing import Any, Mapping

from ..excecoes import ValidacaoErro


class FaixaEtaria:
    __slots__ = ("_minima", "_maxima")
    IDADE_LIMITE = 17

    def __init__(self, idade_minima: int, idade_maxima: int):
        for nome, valor in (("idade mínima", idade_minima), ("idade máxima", idade_maxima)):
            if isinstance(valor, bool) or not isinstance(valor, int):
                raise ValidacaoErro(f"A {nome} precisa ser um número inteiro.")
            if not 0 <= valor <= self.IDADE_LIMITE:
                raise ValidacaoErro(f"A {nome} deve estar entre 0 e {self.IDADE_LIMITE} anos.")
        if idade_minima > idade_maxima:
            raise ValidacaoErro("A idade mínima não pode ser maior que a idade máxima.")
        self._minima = idade_minima
        self._maxima = idade_maxima

    @property
    def idade_minima(self) -> int:
        return self._minima

    @property
    def idade_maxima(self) -> int:
        return self._maxima

    @classmethod
    def de(cls, valor) -> "FaixaEtaria":
        if isinstance(valor, cls):
            return valor
        if isinstance(valor, (tuple, list)) and len(valor) == 2:
            return cls(*valor)
        if isinstance(valor, Mapping):
            return cls(valor.get("idade_minima"), valor.get("idade_maxima"))
        if isinstance(valor, str):
            partes = valor.replace("a", "-").replace("–", "-").split("-")
            try:
                numeros = [int(p.strip()) for p in partes if p.strip()]
            except ValueError:
                numeros = []
            if len(numeros) == 2:
                return cls(*numeros)
            if len(numeros) == 1:
                return cls(numeros[0], numeros[0])
        raise ValidacaoErro("Faixa etária inválida. Exemplo: 5-9 (de 5 a 9 anos).")

    def cobre(self, outra: "FaixaEtaria") -> bool:
        return self._minima <= outra._minima and outra._maxima <= self._maxima

    def para_dicionario(self) -> dict:
        return {"idade_minima": self._minima, "idade_maxima": self._maxima}

    def __contains__(self, idade) -> bool:
        return isinstance(idade, int) and self._minima <= idade <= self._maxima

    def __eq__(self, outro) -> bool:
        if not isinstance(outro, FaixaEtaria):
            return NotImplemented
        return (self._minima, self._maxima) == (outro._minima, outro._maxima)

    def __hash__(self) -> int:
        return hash((self._minima, self._maxima))

    def __str__(self) -> str:
        if self._minima == self._maxima:
            return f"{self._minima} anos"
        return f"{self._minima} a {self._maxima} anos"

    def __repr__(self) -> str:
        return f"FaixaEtaria({self._minima}, {self._maxima})"

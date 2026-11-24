"""Classe DetalhesComplementares (UML: brinde, deslocamento) — RF-07."""

from __future__ import annotations

from typing import Any, Mapping

from ..validacao import sem_acentos, texto_obrigatorio

NAO_SE_APLICA = "não se aplica"
BRINDE_PRIMEIRA_CONTRATACAO = "Brinde de primeira contratação"


class DetalhesComplementares:
    """Benefícios/brindes e condições de deslocamento de um atendimento.

    Os dois campos são obrigatórios no formulário. Quando não há brinde ou
    deslocamento, a gestora informa "não se aplica" (ponto a confirmar com a
    representante, registrado na SRS 1.1). O registro é manual: não há
    cálculo automático de rota.
    """

    def __init__(self, brinde: str, deslocamento: str):
        self.brinde = brinde
        self.deslocamento = deslocamento

    @property
    def brinde(self) -> str:
        return self._brinde

    @brinde.setter
    def brinde(self, valor: str) -> None:
        self._brinde = texto_obrigatorio(valor, "benefícios/brindes")

    @property
    def deslocamento(self) -> str:
        return self._deslocamento

    @deslocamento.setter
    def deslocamento(self, valor: str) -> None:
        self._deslocamento = texto_obrigatorio(valor, "deslocamento")

    @property
    def tem_brinde(self) -> bool:
        return sem_acentos(self._brinde) != sem_acentos(NAO_SE_APLICA)

    @property
    def tem_deslocamento(self) -> bool:
        return sem_acentos(self._deslocamento) != sem_acentos(NAO_SE_APLICA)

    def para_dicionario(self) -> dict:
        return {"brinde": self._brinde, "deslocamento": self._deslocamento}

    @classmethod
    def de_dicionario(cls, dados: Mapping[str, Any]) -> "DetalhesComplementares":
        return cls(dados["brinde"], dados["deslocamento"])

    def __str__(self) -> str:
        return f"Brinde: {self._brinde} | Deslocamento: {self._deslocamento}"

    def __repr__(self) -> str:
        return f"DetalhesComplementares({self._brinde!r}, {self._deslocamento!r})"

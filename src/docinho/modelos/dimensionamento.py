from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .faixa_etaria import FaixaEtaria


@dataclass(frozen=True)
class RegraDimensionamento:
    max_criancas: int
    faixa: FaixaEtaria
    min_recreadores: int
    max_recreadores: int

    def aplica_a(self, quantidade: int, faixa_festa: FaixaEtaria) -> bool:
        return quantidade <= self.max_criancas and self.faixa.cobre(faixa_festa)


DIMENSIONAMENTO_INFORMADO: Tuple[RegraDimensionamento, ...] = (
    RegraDimensionamento(10, FaixaEtaria(3, 12), 2, 2),
    RegraDimensionamento(20, FaixaEtaria(10, 12), 2, 3),
    RegraDimensionamento(50, FaixaEtaria(5, 12), 6, 7),
)


def recomendar_equipe(quantidade: int, faixa: FaixaEtaria) -> Optional[Tuple[int, int]]:
    for regra in DIMENSIONAMENTO_INFORMADO:
        if regra.aplica_a(quantidade, faixa):
            return (regra.min_recreadores, regra.max_recreadores)
    return None

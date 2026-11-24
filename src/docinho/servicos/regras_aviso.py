"""Regras de geração de avisos (RF-08, RN-09) — uso de polimorfismo."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Optional, Tuple

from ..modelos import Lembrete, TipoLembrete

DIAS_LEMBRETE_PRINCIPAL = 14
DIAS_LEMBRETE_REPETIDO = 7


class RegraDeAviso(ABC):
    """Contrato de uma regra de aviso."""

    tipos: Tuple[TipoLembrete, ...] = ()
    refazer_na_remarcacao: bool = True

    @abstractmethod
    def gerar(self, data_festa: date, data_referencia: date) -> Optional[Lembrete]:
        """Cria o lembrete, ou devolve ``None`` quando a regra não se aplica."""


class AvisoConfirmacao(RegraDeAviso):
    """Avisar na confirmação da festa."""

    tipos = (TipoLembrete.CONFIRMACAO,)
    refazer_na_remarcacao = False

    def gerar(self, data_festa, data_referencia):
        return Lembrete(data_referencia, TipoLembrete.CONFIRMACAO)


class AvisoQuatorzeDias(RegraDeAviso):
    """Lembrar 14 dias antes; se a contratação foi com menos de 14 dias, o aviso é imediato (RF-08, RN-09)."""

    tipos = (TipoLembrete.LEMBRETE_14_DIAS, TipoLembrete.AVISO_IMEDIATO)

    def gerar(self, data_festa, data_referencia):
        antecedencia = (data_festa - data_referencia).days
        if antecedencia >= DIAS_LEMBRETE_PRINCIPAL:
            return Lembrete(
                data_festa - timedelta(days=DIAS_LEMBRETE_PRINCIPAL), TipoLembrete.LEMBRETE_14_DIAS
            )
        return Lembrete(data_referencia, TipoLembrete.AVISO_IMEDIATO)


class AvisoSeteDias(RegraDeAviso):
    """Repetir o lembrete uma vez, 7 dias antes (RN-09). Se a data já passou, não há o que lembrar."""

    tipos = (TipoLembrete.LEMBRETE_7_DIAS,)

    def gerar(self, data_festa, data_referencia):
        data_lembrete = data_festa - timedelta(days=DIAS_LEMBRETE_REPETIDO)
        if data_lembrete < data_referencia:
            return None
        return Lembrete(data_lembrete, TipoLembrete.LEMBRETE_7_DIAS)


REGRAS_PADRAO: Tuple[RegraDeAviso, ...] = (AvisoConfirmacao(), AvisoQuatorzeDias(), AvisoSeteDias())

"""Classe RegistroPagamento (UML: valor recebido, saldo pendente) — RF-06.

É apenas um registro informativo: o sistema não processa cobranças nem
movimenta dinheiro (RN-10).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Mapping

from ..excecoes import ValidacaoErro
from ..validacao import moeda, para_data, para_decimal


class RegistroPagamento:
    """Pagamento recebido de uma festa, com o saldo pendente após o registro."""

    __slots__ = ("_valor_recebido", "_data_pagamento", "_saldo_pendente")

    def __init__(self, valor_recebido, data_pagamento, saldo_pendente):
        valor = para_decimal(valor_recebido, "valor recebido")
        if valor <= 0:
            raise ValidacaoErro("O valor recebido precisa ser maior que zero.")
        saldo = para_decimal(saldo_pendente, "saldo pendente")
        if saldo < 0:
            raise ValidacaoErro("O saldo pendente não pode ser negativo.")
        self._valor_recebido: Decimal = valor
        self._data_pagamento: date = para_data(data_pagamento, "data do pagamento")
        self._saldo_pendente: Decimal = saldo

    @property
    def valor_recebido(self) -> Decimal:
        return self._valor_recebido

    @property
    def data_pagamento(self) -> date:
        return self._data_pagamento

    @property
    def saldo_pendente(self) -> Decimal:
        """Saldo da festa logo após este pagamento."""
        return self._saldo_pendente

    def para_dicionario(self) -> dict:
        return {
            "valor_recebido": str(self._valor_recebido),
            "data_pagamento": self._data_pagamento.isoformat(),
            "saldo_pendente": str(self._saldo_pendente),
        }

    @classmethod
    def de_dicionario(cls, dados: Mapping[str, Any]) -> "RegistroPagamento":
        return cls(dados["valor_recebido"], dados["data_pagamento"], dados["saldo_pendente"])

    def __str__(self) -> str:
        return (
            f"{self._data_pagamento:%d/%m/%Y}: recebido {moeda(self._valor_recebido)} "
            f"(saldo {moeda(self._saldo_pendente)})"
        )

    def __repr__(self) -> str:
        return (
            f"RegistroPagamento({str(self._valor_recebido)!r}, "
            f"{self._data_pagamento.isoformat()!r}, {str(self._saldo_pendente)!r})"
        )

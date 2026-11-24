"""Acompanhamento de valores e pagamentos (RF-06, RN-02, RN-03, RN-10)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from ..modelos import Contratante, Festa, RegistroPagamento, SituacaoFesta
from ..persistencia import Armazenamento
from ..validacao import moeda, para_data

_ZERO = Decimal("0.00")


@dataclass(frozen=True, eq=False)
class SituacaoFinanceira:
    """Totais de um contratante (tela 'Financeiro' do protótipo)."""

    contratante: Contratante
    total_contratado: Decimal
    total_recebido: Decimal
    saldo_pendente: Decimal
    quantidade_festas: int

    def __str__(self) -> str:
        return (
            f"{self.contratante.nome}: contratado {moeda(self.total_contratado)} | "
            f"recebido {moeda(self.total_recebido)} | a receber {moeda(self.saldo_pendente)}"
        )


@dataclass(frozen=True, eq=False)
class CreditoRetido:
    """Valor retido por cancelamento, utilizável em até 1 ano (RN-03)."""

    festa: Festa
    valor: Decimal
    valido_ate: date

    def __str__(self) -> str:
        return (
            f"Festa #{self.festa.id} ({self.festa.contratante.nome}): crédito de "
            f"{moeda(self.valor)} válido até {self.valido_ate:%d/%m/%Y}"
        )


class ServicoFinanceiro:
    def __init__(self, armazenamento: Armazenamento):
        self._arm = armazenamento

    def registrar_pagamento(self, festa_id: int, valor, data_pagamento=None) -> RegistroPagamento:
        """Registra o pagamento. Se a gravação falhar, o pagamento é desfeito e valor, evento e saldo permanecem consistentes (RNF-03, CS-05)."""
        festa = self._arm.obter_festa(festa_id)
        with self._arm.transacao():
            registro = festa.registrar_pagamento(valor, data_pagamento)
        return registro

    def saldo_pendente(self, festa_id: int) -> Decimal:
        return self._arm.obter_festa(festa_id).saldo_pendente

    def situacao_por_contratante(self) -> List[SituacaoFinanceira]:
        """Totais por contratante, sem contar festas canceladas."""
        acumulado: Dict[int, List] = {}
        for festa in self._arm.festas.values():
            if festa.situacao is SituacaoFesta.CANCELADA:
                continue
            linha = acumulado.setdefault(festa.contratante.id, [festa.contratante, _ZERO, _ZERO, 0])
            linha[1] += festa.valor_combinado
            linha[2] += festa.total_recebido
            linha[3] += 1
        resultado = [
            SituacaoFinanceira(c, contratado, recebido, contratado - recebido, quantidade)
            for c, contratado, recebido, quantidade in acumulado.values()
        ]
        return sorted(resultado, key=lambda s: s.contratante.nome.casefold())

    def total_a_receber(self) -> Decimal:
        return sum((s.saldo_pendente for s in self.situacao_por_contratante()), _ZERO)

    def creditos_retidos(self, hoje: Optional[date] = None) -> List[CreditoRetido]:
        """Créditos de festas canceladas ainda dentro do prazo de 1 ano."""
        dia = para_data(hoje) if hoje else date.today()
        creditos = [
            CreditoRetido(f, f.credito_retido, f.credito_valido_ate)
            for f in self._arm.festas.values()
            if f.situacao is SituacaoFesta.CANCELADA
            and f.credito_retido > 0
            and f.credito_valido_ate is not None
            and f.credito_valido_ate >= dia
        ]
        return sorted(creditos, key=lambda c: c.valido_ate)

"""Classe Lembrete (UML: data prevista, tipo, situação) — RF-08, RN-09."""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Optional

from ..excecoes import RegraDeNegocioErro
from ..validacao import para_data
from .enumeracoes import SituacaoLembrete, TipoLembrete

_ROTULOS = {
    TipoLembrete.CONFIRMACAO: "Aviso de confirmação",
    TipoLembrete.LEMBRETE_14_DIAS: "Lembrete de 14 dias",
    TipoLembrete.AVISO_IMEDIATO: "Aviso imediato (contratação com menos de 14 dias)",
    TipoLembrete.LEMBRETE_7_DIAS: "Lembrete de 7 dias",
}


class Lembrete:
    def __init__(
        self,
        data_prevista,
        tipo: TipoLembrete,
        situacao: SituacaoLembrete = SituacaoLembrete.PENDENTE,
        data_envio=None,
    ):
        self._data_prevista: date = para_data(data_prevista, "data prevista do aviso")
        self._tipo = TipoLembrete(tipo)
        self._situacao = SituacaoLembrete(situacao)
        self._data_envio: Optional[date] = para_data(data_envio) if data_envio else None

    @property
    def data_prevista(self) -> date:
        return self._data_prevista

    @property
    def tipo(self) -> TipoLembrete:
        return self._tipo

    @property
    def situacao(self) -> SituacaoLembrete:
        return self._situacao

    @property
    def data_envio(self) -> Optional[date]:
        return self._data_envio

    @property
    def pendente(self) -> bool:
        return self._situacao is SituacaoLembrete.PENDENTE

    def deve_aparecer_em(self, dia: date) -> bool:
        """Aviso pendente cuja data prevista já chegou (aparece até ser tratado)."""
        return self.pendente and self._data_prevista <= dia

    def marcar_enviado(self, data_envio: Optional[date] = None) -> None:
        """Bruna registra que enviou a mensagem manualmente pelo WhatsApp."""
        if not self.pendente:
            raise RegraDeNegocioErro("Somente avisos pendentes podem ser marcados como enviados.")
        self._situacao = SituacaoLembrete.ENVIADO
        self._data_envio = para_data(data_envio) if data_envio else date.today()

    def cancelar(self) -> None:
        """Aviso substituído (remarcação) ou sem efeito (festa cancelada)."""
        if self.pendente:
            self._situacao = SituacaoLembrete.CANCELADO

    def para_dicionario(self) -> dict:
        return {
            "data_prevista": self._data_prevista.isoformat(),
            "tipo": self._tipo.value,
            "situacao": self._situacao.value,
            "data_envio": self._data_envio.isoformat() if self._data_envio else None,
        }

    @classmethod
    def de_dicionario(cls, dados: Mapping[str, Any]) -> "Lembrete":
        return cls(dados["data_prevista"], dados["tipo"], dados["situacao"], dados.get("data_envio"))

    def __str__(self) -> str:
        return f"{self._data_prevista:%d/%m/%Y} — {_ROTULOS[self._tipo]} [{self._situacao.value}]"

    def __repr__(self) -> str:
        return (
            f"Lembrete({self._data_prevista.isoformat()!r}, {self._tipo.value!r}, "
            f"{self._situacao.value!r})"
        )

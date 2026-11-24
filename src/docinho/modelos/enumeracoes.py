from __future__ import annotations

from enum import Enum


class SituacaoFesta(str, Enum):
    CONFIRMADA = "confirmada"
    REALIZADA = "realizada"
    QUITADA = "quitada"
    CANCELADA = "cancelada"


class TipoLembrete(str, Enum):
    CONFIRMACAO = "confirmacao"
    LEMBRETE_14_DIAS = "lembrete_14_dias"
    AVISO_IMEDIATO = "aviso_imediato"
    LEMBRETE_7_DIAS = "lembrete_7_dias"


class SituacaoLembrete(str, Enum):
    PENDENTE = "pendente"
    ENVIADO = "enviado"
    CANCELADO = "cancelado"


class TipoConflito(str, Enum):
    INDISPONIVEL = "indisponivel"
    SOBREPOSICAO = "sobreposicao"
    INTERVALO_INSUFICIENTE = "intervalo_insuficiente"

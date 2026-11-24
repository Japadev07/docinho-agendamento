"""Enumerações do domínio."""

from __future__ import annotations

from enum import Enum


class SituacaoFesta(str, Enum):
    """Situações conferidas na SRS (RF-03)."""

    CONFIRMADA = "confirmada"
    REALIZADA = "realizada"
    QUITADA = "quitada"
    CANCELADA = "cancelada"


class TipoLembrete(str, Enum):
    """Tipos de aviso previstos em RF-08 / RN-09."""

    CONFIRMACAO = "confirmacao"
    LEMBRETE_14_DIAS = "lembrete_14_dias"
    AVISO_IMEDIATO = "aviso_imediato"  # contratação com menos de 14 dias
    LEMBRETE_7_DIAS = "lembrete_7_dias"


class SituacaoLembrete(str, Enum):
    PENDENTE = "pendente"
    ENVIADO = "enviado"  # a gestora marcou que enviou manualmente pelo WhatsApp
    CANCELADO = "cancelado"  # substituído por remarcação ou festa cancelada


class TipoConflito(str, Enum):
    """Incompatibilidades sinalizadas na escala (RF-04, RN-05, RN-07)."""

    INDISPONIVEL = "indisponivel"
    SOBREPOSICAO = "sobreposicao"
    INTERVALO_INSUFICIENTE = "intervalo_insuficiente"

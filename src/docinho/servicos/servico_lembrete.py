"""Organização dos avisos para consulta da gestora (RF-08, RN-09)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from typing import Iterable, List, Optional

from ..excecoes import NaoEncontradoErro
from ..modelos import Festa, Lembrete, SituacaoFesta
from ..persistencia import Armazenamento
from ..validacao import para_data
from .regras_aviso import REGRAS_PADRAO, RegraDeAviso

HORARIO_PREFERIDO_ENVIO = time(9, 0)


@dataclass(frozen=True, eq=False)
class Aviso:
    """Um lembrete pendente junto da festa a que pertence."""

    festa: Festa
    lembrete: Lembrete
    indice: int

    def __str__(self) -> str:
        return (
            f"Festa #{self.festa.id} ({self.festa.contratante.nome}, "
            f"{self.festa.data:%d/%m/%Y}) — {self.lembrete} "
            f"— enviar até {HORARIO_PREFERIDO_ENVIO:%H:%M}"
        )


class ServicoLembrete:
    def __init__(self, armazenamento: Armazenamento, regras: Optional[Iterable[RegraDeAviso]] = None):
        self._arm = armazenamento
        self._regras = tuple(regras) if regras is not None else REGRAS_PADRAO

    def gerar_iniciais(self, festa: Festa, data_confirmacao: date) -> List[Lembrete]:
        """Cria os avisos de uma festa recém-confirmada (não grava)."""
        criados = []
        for regra in self._regras:
            lembrete = regra.gerar(festa.data, data_confirmacao)
            if lembrete is not None:
                festa.adicionar_lembrete(lembrete)
                criados.append(lembrete)
        return criados

    def refazer(self, festa: Festa, data_referencia: date) -> List[Lembrete]:
        """Remarcação: cancela os avisos pendentes que dependem da data e recalcula a partir da data da remarcação (RN-09). Não grava."""
        regras = [r for r in self._regras if r.refazer_na_remarcacao]
        tipos = {t for r in regras for t in r.tipos}
        for lembrete in festa.lembretes:
            if lembrete.tipo in tipos:
                lembrete.cancelar()
        criados = []
        for regra in regras:
            lembrete = regra.gerar(festa.data, data_referencia)
            if lembrete is not None:
                festa.adicionar_lembrete(lembrete)
                criados.append(lembrete)
        return criados

    def avisos_pendentes(self, dia: Optional[date] = None) -> List[Aviso]:
        """Avisos de festas não canceladas cuja data prevista já chegou e que ainda não foram marcados como enviados, em ordem de data."""
        dia = para_data(dia) if dia else date.today()
        avisos = []
        for festa in self._arm.festas.values():
            if festa.situacao is SituacaoFesta.CANCELADA:
                continue
            for indice, lembrete in enumerate(festa.lembretes):
                if lembrete.deve_aparecer_em(dia):
                    avisos.append(Aviso(festa, lembrete, indice))
        return sorted(avisos, key=lambda a: (a.lembrete.data_prevista, a.festa.data, a.festa.id))

    def marcar_enviado(self, festa_id: int, indice: int, data_envio: Optional[date] = None) -> Lembrete:
        """Bruna registra que já enviou o aviso pelo WhatsApp."""
        festa = self._arm.obter_festa(festa_id)
        lembretes = festa.lembretes
        if not 0 <= indice < len(lembretes):
            raise NaoEncontradoErro(f"Aviso {indice} não existe na festa {festa_id}.")
        with self._arm.transacao():
            lembretes[indice].marcar_enviado(data_envio)
        return lembretes[indice]

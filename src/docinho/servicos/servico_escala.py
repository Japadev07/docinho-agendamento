"""Escala de recreadores: conflitos e dimensionamento (RF-04, RN-05, RN-06, RN-07)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple

from ..excecoes import ConflitoEscalaErro
from ..modelos import Festa, Recreador, SituacaoFesta, TipoConflito, recomendar_equipe
from ..persistencia import Armazenamento
from ..validacao import para_data, para_hora

INTERVALO_MINIMO = timedelta(minutes=60)


@dataclass(frozen=True, eq=False)
class Conflito:
    tipo: TipoConflito
    recreador: Recreador
    festa_conflitante: Optional[Festa] = None

    def __str__(self) -> str:
        nome = self.recreador.identificacao
        if self.tipo is TipoConflito.INDISPONIVEL:
            return f"{nome} está marcado(a) como indisponível."
        outra = self.festa_conflitante
        periodo = f"{outra.inicio:%H:%M}–{outra.termino:%H:%M} (festa #{outra.id})"
        if self.tipo is TipoConflito.SOBREPOSICAO:
            return f"{nome} já está em outra festa no mesmo horário: {periodo}."
        minutos = int(INTERVALO_MINIMO.total_seconds() // 60)
        return f"{nome} teria menos de {minutos} min de intervalo para a festa {periodo}."


class ServicoEscala:
    def __init__(self, armazenamento: Armazenamento):
        self._arm = armazenamento

    def verificar_janela(
        self,
        recreador: Recreador,
        data: date,
        inicio: time,
        termino: time,
        ignorar_festa_id: Optional[int] = None,
    ) -> List[Conflito]:
        """Conflitos do recreador para uma data e horário."""
        data = para_data(data)
        inicio_dt = datetime.combine(data, para_hora(inicio))
        termino_dt = datetime.combine(data, para_hora(termino))
        conflitos: List[Conflito] = []
        if not recreador.disponibilidade:
            conflitos.append(Conflito(TipoConflito.INDISPONIVEL, recreador))
        for outra in self._arm.festas.values():
            if ignorar_festa_id is not None and outra.id == ignorar_festa_id:
                continue
            if outra.situacao is SituacaoFesta.CANCELADA or outra.data != data:
                continue
            if recreador not in outra.recreadores:
                continue
            if inicio_dt < outra.termino_dt and outra.inicio_dt < termino_dt:
                conflitos.append(Conflito(TipoConflito.SOBREPOSICAO, recreador, outra))
                continue
            intervalo = (
                outra.inicio_dt - termino_dt if termino_dt <= outra.inicio_dt else inicio_dt - outra.termino_dt
            )
            if intervalo < INTERVALO_MINIMO:
                conflitos.append(Conflito(TipoConflito.INTERVALO_INSUFICIENTE, recreador, outra))
        return conflitos

    def verificar(self, recreador: Recreador, festa: Festa) -> List[Conflito]:
        """Conflitos do recreador para a data e horário da festa."""
        return self.verificar_janela(
            recreador, festa.data, festa.inicio, festa.termino, ignorar_festa_id=festa.id
        )

    def recreadores_disponiveis(self, festa: Festa) -> List[Recreador]:
        """Recreadores ainda não escalados na festa e sem nenhum conflito para a data e o horário dela (apoio à decisão da gestora)."""
        return [
            r
            for r in self._arm.recreadores.values()
            if r not in festa.recreadores and not self.verificar(r, festa)
        ]

    @staticmethod
    def recomendar(festa: Festa) -> Optional[Tuple[int, int]]:
        """(mínimo, máximo) informado no formulário, ou None se a combinação de quantidade e faixa etária não está coberta."""
        return recomendar_equipe(festa.quantidade_criancas, festa.faixa_etaria)

    def alertas_equipe(self, festa: Festa) -> List[str]:
        recomendado = self.recomendar(festa)
        escalados = len(festa.recreadores)
        if recomendado is None:
            return []
        minimo, maximo = recomendado
        faixa_texto = f"{minimo}" if minimo == maximo else f"{minimo} a {maximo}"
        if escalados < minimo:
            return [
                f"Equipe abaixo do informado pela Docinho: {faixa_texto} recreadores "
                f"para esta festa; escalados: {escalados}."
            ]
        if escalados > maximo:
            return [
                f"Equipe acima do informado pela Docinho: {faixa_texto} recreadores "
                f"para esta festa; escalados: {escalados}."
            ]
        return []

    def alocar(self, festa_id: int, recreador_id: int, forcar: bool = False) -> List[Conflito]:
        """Escala o recreador na festa."""
        festa = self._arm.obter_festa(festa_id)
        recreador = self._arm.obter_recreador(recreador_id)
        conflitos = self.verificar(recreador, festa)
        if conflitos and not forcar:
            raise ConflitoEscalaErro(conflitos)
        with self._arm.transacao():
            festa.adicionar_recreador(recreador)
        return conflitos

    def desalocar(self, festa_id: int, recreador_id: int) -> None:
        festa = self._arm.obter_festa(festa_id)
        recreador = self._arm.obter_recreador(recreador_id)
        with self._arm.transacao():
            festa.remover_recreador(recreador)

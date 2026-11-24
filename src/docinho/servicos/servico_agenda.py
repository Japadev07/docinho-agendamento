from __future__ import annotations

from datetime import date
from typing import Iterable, Iterator, Optional

from ..modelos import Festa, SituacaoFesta
from ..persistencia import Armazenamento
from ..validacao import para_data


class Agenda:
    def __init__(self, festas: Iterable[Festa]):
        self._festas = sorted(festas)

    def __len__(self) -> int:
        return len(self._festas)

    def __iter__(self) -> Iterator[Festa]:
        return iter(self._festas)

    def __getitem__(self, indice):
        return self._festas[indice]

    def __contains__(self, festa) -> bool:
        return any(festa is f for f in self._festas)

    def __str__(self) -> str:
        if not self._festas:
            return "Agenda vazia."
        return "\n".join(str(f) for f in self._festas)

    def __repr__(self) -> str:
        return f"Agenda({len(self._festas)} festas)"

    def do_dia(self, dia: date) -> "Agenda":
        dia = para_data(dia)
        return Agenda(f for f in self._festas if f.data == dia)

    def com_situacao(self, situacao: SituacaoFesta) -> "Agenda":
        situacao = SituacaoFesta(situacao)
        return Agenda(f for f in self._festas if f.situacao is situacao)


class ServicoAgenda:
    def __init__(self, armazenamento: Armazenamento):
        self._arm = armazenamento

    def consultar(
        self, data_inicial=None, data_final=None, situacao: Optional[SituacaoFesta] = None
    ) -> Agenda:
        inicio = para_data(data_inicial) if data_inicial else None
        fim = para_data(data_final) if data_final else None
        festas = self._arm.festas.values()
        if inicio:
            festas = [f for f in festas if f.data >= inicio]
        if fim:
            festas = [f for f in festas if f.data <= fim]
        agenda = Agenda(festas)
        return agenda.com_situacao(situacao) if situacao else agenda

    def do_dia(self, dia) -> Agenda:
        return self.consultar(dia, dia)

    def proximas(self, hoje=None, limite: int = 5) -> Agenda:
        dia = para_data(hoje) if hoje else date.today()
        agenda = self.consultar(data_inicial=dia, situacao=SituacaoFesta.CONFIRMADA)
        return Agenda(list(agenda)[:limite])

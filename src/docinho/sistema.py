from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from .persistencia import Armazenamento, Repositorio, RepositorioJSON, RepositorioMemoria
from .servicos import (
    ServicoAgenda,
    ServicoContratante,
    ServicoEscala,
    ServicoFesta,
    ServicoFinanceiro,
    ServicoLembrete,
    ServicoRecreador,
    ServicoResumo,
)


class Sistema:
    def __init__(self, repositorio: Optional[Repositorio] = None):
        self.repositorio = repositorio if repositorio is not None else RepositorioMemoria()
        self.armazenamento = Armazenamento(self.repositorio)
        self.contratantes = ServicoContratante(self.armazenamento)
        self.recreadores = ServicoRecreador(self.armazenamento)
        self.escala = ServicoEscala(self.armazenamento)
        self.lembretes = ServicoLembrete(self.armazenamento)
        self.festas = ServicoFesta(self.armazenamento, self.escala, self.lembretes)
        self.financeiro = ServicoFinanceiro(self.armazenamento)
        self.agenda = ServicoAgenda(self.armazenamento)
        self.resumos = ServicoResumo(self.armazenamento, self.escala)

    @classmethod
    def com_arquivo(cls, caminho: Union[str, Path]) -> "Sistema":
        return cls(RepositorioJSON(caminho))

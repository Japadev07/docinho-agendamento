from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..modelos import Festa, SituacaoFesta
from ..persistencia import Armazenamento
from ..validacao import moeda
from .servico_escala import ServicoEscala


@dataclass(eq=False)
class ResumoEvento:
    festa: Festa
    alertas: List[str] = field(default_factory=list)
    recomendacao_equipe: str = ""

    def __str__(self) -> str:
        f = self.festa
        linhas = [
            f"=== FESTA #{f.id} — {f.situacao.value.upper()} ===",
            "",
            "CONTRATANTE",
            f"  {f.contratante}",
            "",
            "PROGRAMAÇÃO",
            f"  Data: {f.data:%d/%m/%Y}   Horário: {f.inicio:%H:%M} às {f.termino:%H:%M}",
            f"  Endereço: {f.endereco}",
            f"  Crianças: {f.quantidade_criancas} ({f.faixa_etaria})",
            "  Atividades: " + "; ".join(str(a) for a in f.atividades),
            f"  {f.detalhes}",
            "",
            "EQUIPE",
            "  " + (", ".join(r.identificacao for r in f.recreadores) or "nenhum recreador escalado"),
        ]
        if self.recomendacao_equipe:
            linhas.append(f"  {self.recomendacao_equipe}")
        linhas += [
            "",
            "VALORES",
            f"  Combinado: {moeda(f.valor_combinado)}   Entrada prevista (50%): {moeda(f.entrada_prevista)}",
            f"  Recebido: {moeda(f.total_recebido)}   Saldo pendente: {moeda(f.saldo_pendente)}",
            "  Data reservada (entrada paga): " + ("sim" if f.data_reservada else "não"),
        ]
        for pagamento in f.pagamentos:
            linhas.append(f"    - {pagamento}")
        if f.situacao is SituacaoFesta.CANCELADA and f.credito_retido > 0:
            linhas.append(
                f"  Crédito retido: {moeda(f.credito_retido)} válido até {f.credito_valido_ate:%d/%m/%Y}"
            )
        linhas += ["", "AVISOS"]
        linhas += [f"  - {lembrete}" for lembrete in f.lembretes] or ["  (nenhum)"]
        if self.alertas:
            linhas += ["", "ALERTAS"] + [f"  ! {alerta}" for alerta in self.alertas]
        return "\n".join(linhas)


class ServicoResumo:
    def __init__(self, armazenamento: Armazenamento, escala: ServicoEscala):
        self._arm = armazenamento
        self._escala = escala

    def gerar(self, festa_id: int) -> ResumoEvento:
        festa = self._arm.obter_festa(festa_id)
        alertas: List[str] = []
        if festa.situacao is not SituacaoFesta.CANCELADA:
            alertas += self._escala.alertas_equipe(festa)
            for recreador in festa.recreadores:
                alertas += [str(c) for c in self._escala.verificar(recreador, festa)]
            for atividade in festa.atividades_fora_da_faixa():
                alertas.append(
                    f"A atividade '{atividade.nome}' é indicada para {atividade.indicacao}, "
                    f"mas a festa é para {festa.faixa_etaria}."
                )
            if festa.confirmada and not festa.entrada_paga:
                alertas.append("Entrada ainda não recebida: a data não está reservada (RN-02).")
            if festa.situacao is SituacaoFesta.REALIZADA and festa.saldo_pendente > 0:
                alertas.append(f"Festa realizada com saldo pendente de {moeda(festa.saldo_pendente)}.")
        recomendado = self._escala.recomendar(festa)
        if recomendado is None:
            texto = "Combinação sem referência no formulário: a escala fica a critério da gestora."
        else:
            minimo, maximo = recomendado
            intervalo = f"{minimo}" if minimo == maximo else f"{minimo} a {maximo}"
            texto = f"Informado pela Docinho para esta combinação: {intervalo} recreadores."
        return ResumoEvento(festa, alertas, texto)

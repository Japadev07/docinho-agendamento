from __future__ import annotations

from datetime import date
from typing import Iterable, List, Optional

from ..excecoes import (
    CampoObrigatorioErro,
    ConflitoEscalaErro,
    TransicaoInvalidaErro,
    ValidacaoErro,
)
from ..modelos import (
    BRINDE_PRIMEIRA_CONTRATACAO,
    NAO_SE_APLICA,
    Atividade,
    DetalhesComplementares,
    FaixaEtaria,
    Festa,
)
from ..persistencia import Armazenamento
from ..validacao import inteiro_positivo, para_data, para_hora, sem_acentos
from .servico_escala import ServicoEscala
from .servico_lembrete import ServicoLembrete


def _vazio(valor) -> bool:
    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip()
    if isinstance(valor, (list, tuple, set)):
        return len(valor) == 0
    return False


class ServicoFesta:
    def __init__(self, armazenamento: Armazenamento, escala: ServicoEscala, lembretes: ServicoLembrete):
        self._arm = armazenamento
        self._escala = escala
        self._lembretes = lembretes

    def obter(self, festa_id: int) -> Festa:
        return self._arm.obter_festa(festa_id)

    def festas_do_contratante(self, contratante_id: int) -> List[Festa]:
        return sorted(f for f in self._arm.festas.values() if f.contratante.id == contratante_id)

    @staticmethod
    def _aplicar_brinde_primeira_contratacao(brinde: Optional[str], primeira: bool) -> Optional[str]:
        if not primeira:
            return brinde
        if _vazio(brinde) or sem_acentos(brinde.strip()) == sem_acentos(NAO_SE_APLICA):
            return BRINDE_PRIMEIRA_CONTRATACAO
        if sem_acentos(BRINDE_PRIMEIRA_CONTRATACAO) in sem_acentos(brinde):
            return brinde
        return f"{brinde.strip()} + {BRINDE_PRIMEIRA_CONTRATACAO}"

    def agendar(
        self,
        contratante_id: Optional[int],
        data,
        inicio,
        termino,
        endereco: Optional[str],
        quantidade_criancas: Optional[int],
        faixa_etaria,
        valor_combinado,
        atividades: Optional[Iterable],
        recreadores_ids: Optional[Iterable[int]],
        brinde: Optional[str] = None,
        deslocamento: Optional[str] = None,
        data_confirmacao=None,
        forcar_escala: bool = False,
    ) -> Festa:
        hoje = para_data(data_confirmacao) if data_confirmacao else date.today()
        contratante = self._arm.obter_contratante(contratante_id) if contratante_id is not None else None
        primeira = contratante is not None and not self.festas_do_contratante(contratante.id)
        brinde = self._aplicar_brinde_primeira_contratacao(brinde, primeira)
        ids_recreadores = list(recreadores_ids) if recreadores_ids is not None else None

        obrigatorios = [
            ("contratante", contratante),
            ("data", data),
            ("horário de início", inicio),
            ("horário de término", termino),
            ("endereço", endereco),
            ("quantidade de crianças", quantidade_criancas),
            ("faixa etária", faixa_etaria),
            ("valor combinado", valor_combinado),
            ("brincadeiras previstas", atividades),
            ("recreadores escalados", ids_recreadores),
            ("benefícios/brindes", brinde),
            ("deslocamento", deslocamento),
        ]
        faltando = [nome for nome, valor in obrigatorios if _vazio(valor)]
        if faltando:
            raise CampoObrigatorioErro(faltando)

        if len(set(ids_recreadores)) != len(ids_recreadores):
            raise ValidacaoErro("Há recreador repetido na escala da festa.")
        recreadores = [self._arm.obter_recreador(rid) for rid in ids_recreadores]

        festa = Festa(
            contratante=contratante,
            data=data,
            inicio=inicio,
            termino=termino,
            endereco=endereco,
            quantidade_criancas=quantidade_criancas,
            faixa_etaria=faixa_etaria,
            valor_combinado=valor_combinado,
            atividades=atividades,
            detalhes=DetalhesComplementares(brinde, deslocamento),
            data_confirmacao=hoje,
        )
        if festa.data < hoje:
            raise ValidacaoErro("A data da festa não pode ser anterior à data da confirmação.")

        conflitos = [c for r in recreadores for c in self._escala.verificar(r, festa)]
        if conflitos and not forcar_escala:
            raise ConflitoEscalaErro(conflitos)

        for recreador in recreadores:
            festa.adicionar_recreador(recreador)
        self._lembretes.gerar_iniciais(festa, hoje)
        with self._arm.transacao():
            self._arm.adicionar_festa(festa)
        return festa

    def remarcar(
        self,
        festa_id: int,
        nova_data,
        inicio=None,
        termino=None,
        data_remarcacao=None,
        forcar_escala: bool = False,
    ) -> Festa:
        festa = self._arm.obter_festa(festa_id)
        if not festa.confirmada:
            raise TransicaoInvalidaErro(
                f"Só é possível remarcar festas confirmadas (esta está {festa.situacao.value})."
            )
        hoje = para_data(data_remarcacao) if data_remarcacao else date.today()
        data = para_data(nova_data, "nova data")
        if data < hoje:
            raise ValidacaoErro("A nova data não pode ser anterior à data da remarcação.")
        novo_inicio = para_hora(inicio, "horário de início") if inicio is not None else festa.inicio
        novo_termino = para_hora(termino, "horário de término") if termino is not None else festa.termino
        if novo_termino <= novo_inicio:
            raise ValidacaoErro("O horário de término precisa ser depois do horário de início.")

        conflitos = [
            c
            for r in festa.recreadores
            for c in self._escala.verificar_janela(r, data, novo_inicio, novo_termino, ignorar_festa_id=festa.id)
        ]
        if conflitos and not forcar_escala:
            raise ConflitoEscalaErro(conflitos)

        with self._arm.transacao():
            festa.remarcar(data, novo_inicio, novo_termino)
            self._lembretes.refazer(festa, hoje)
        return festa

    def marcar_realizada(self, festa_id: int, hoje: Optional[date] = None) -> Festa:
        festa = self._arm.obter_festa(festa_id)
        with self._arm.transacao():
            festa.marcar_realizada(hoje)
        return festa

    def cancelar(self, festa_id: int, data_cancelamento=None) -> Festa:
        festa = self._arm.obter_festa(festa_id)
        with self._arm.transacao():
            festa.cancelar(data_cancelamento)
        return festa

    def atualizar_criancas_e_atividades(
        self,
        festa_id: int,
        quantidade_criancas: Optional[int] = None,
        faixa_etaria=None,
        atividades: Optional[Iterable] = None,
    ) -> Festa:
        festa = self._arm.obter_festa(festa_id)
        quantidade = inteiro_positivo(quantidade_criancas, "quantidade de crianças") if quantidade_criancas is not None else None
        faixa = FaixaEtaria.de(faixa_etaria) if faixa_etaria is not None else None
        lista = None
        if atividades is not None:
            lista = [Atividade.de(a) for a in ([atividades] if isinstance(atividades, (str, Atividade)) else atividades)]
            if not lista:
                raise ValidacaoErro("Informe ao menos uma brincadeira prevista.")
        with self._arm.transacao():
            if quantidade is not None:
                festa.quantidade_criancas = quantidade
            if faixa is not None:
                festa.faixa_etaria = faixa
            if lista is not None:
                festa.atividades = lista
        return festa

    def atualizar_detalhes(
        self, festa_id: int, brinde: Optional[str] = None, deslocamento: Optional[str] = None
    ) -> Festa:
        festa = self._arm.obter_festa(festa_id)
        novo = DetalhesComplementares(
            brinde if brinde is not None else festa.detalhes.brinde,
            deslocamento if deslocamento is not None else festa.detalhes.deslocamento,
        )
        with self._arm.transacao():
            festa.detalhes = novo
        return festa

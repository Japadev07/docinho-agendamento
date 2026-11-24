"""Classe Festa — centro do diagrama de classes (RF-02, RF-03, RF-05, RF-06)."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable, List, Mapping, Optional, Tuple

from ..excecoes import RegraDeNegocioErro, TransicaoInvalidaErro, ValidacaoErro
from ..validacao import (
    CENTAVOS,
    inteiro_positivo,
    moeda,
    para_data,
    para_decimal,
    para_hora,
    somar_um_ano,
    texto_obrigatorio,
)
from .atividade import Atividade
from .base import EntidadeBase
from .contratante import Contratante
from .detalhes import DetalhesComplementares
from .enumeracoes import SituacaoFesta
from .faixa_etaria import FaixaEtaria
from .lembrete import Lembrete
from .pagamento import RegistroPagamento
from .recreador import Recreador

_ZERO = Decimal("0.00")


class Festa(EntidadeBase):
    """Festa contratada, com agenda, equipe, atividades, valores e avisos."""

    PERCENTUAL_ENTRADA = Decimal("0.5")

    _TRANSICOES = {
        SituacaoFesta.CONFIRMADA: {SituacaoFesta.REALIZADA, SituacaoFesta.CANCELADA},
        SituacaoFesta.REALIZADA: {SituacaoFesta.QUITADA},
        SituacaoFesta.QUITADA: set(),
        SituacaoFesta.CANCELADA: set(),
    }

    def __init__(
        self,
        contratante: Contratante,
        data,
        inicio,
        termino,
        endereco: str,
        quantidade_criancas: int,
        faixa_etaria,
        valor_combinado,
        atividades: Iterable,
        detalhes: DetalhesComplementares,
        data_confirmacao=None,
        id: Optional[int] = None,
    ):
        super().__init__(id)
        if not isinstance(contratante, Contratante):
            raise ValidacaoErro("A festa precisa estar vinculada a um contratante.")
        self._recreadores: List[Recreador] = []
        self._pagamentos: List[RegistroPagamento] = []
        self._lembretes: List[Lembrete] = []
        self._contratante = contratante
        self._situacao = SituacaoFesta.CONFIRMADA
        self._data_cancelamento: Optional[date] = None
        self._credito_retido: Decimal = _ZERO
        self._credito_valido_ate: Optional[date] = None
        self._data_confirmacao = para_data(data_confirmacao) if data_confirmacao else date.today()
        self.data = data
        self._inicio: Optional[time] = None
        self._termino: Optional[time] = None
        self.definir_horario(inicio, termino)
        self.endereco = endereco
        self.quantidade_criancas = quantidade_criancas
        self.faixa_etaria = faixa_etaria
        self.valor_combinado = valor_combinado
        self.atividades = atividades
        self.detalhes = detalhes

    @property
    def contratante(self) -> Contratante:
        return self._contratante

    @property
    def data(self) -> date:
        return self._data

    @data.setter
    def data(self, valor) -> None:
        self._data = para_data(valor, "data da festa")

    @property
    def inicio(self) -> time:
        return self._inicio

    @property
    def termino(self) -> time:
        return self._termino

    def definir_horario(self, inicio, termino) -> None:
        """Início e término são validados em conjunto: o término vem depois."""
        hora_inicio = para_hora(inicio, "horário de início")
        hora_termino = para_hora(termino, "horário de término")
        if hora_termino <= hora_inicio:
            raise ValidacaoErro("O horário de término precisa ser depois do horário de início.")
        self._inicio, self._termino = hora_inicio, hora_termino

    @property
    def inicio_dt(self) -> datetime:
        return datetime.combine(self._data, self._inicio)

    @property
    def termino_dt(self) -> datetime:
        return datetime.combine(self._data, self._termino)

    @property
    def endereco(self) -> str:
        return self._endereco

    @endereco.setter
    def endereco(self, valor: str) -> None:
        self._endereco = texto_obrigatorio(valor, "endereço")

    @property
    def quantidade_criancas(self) -> int:
        return self._quantidade_criancas

    @quantidade_criancas.setter
    def quantidade_criancas(self, valor: int) -> None:
        self._quantidade_criancas = inteiro_positivo(valor, "quantidade de crianças")

    @property
    def faixa_etaria(self) -> FaixaEtaria:
        return self._faixa_etaria

    @faixa_etaria.setter
    def faixa_etaria(self, valor) -> None:
        self._faixa_etaria = FaixaEtaria.de(valor)

    @property
    def atividades(self) -> Tuple[Atividade, ...]:
        return tuple(self._atividades)

    @atividades.setter
    def atividades(self, valor: Iterable) -> None:
        if isinstance(valor, (str, Atividade)):
            valor = [valor]
        lista = [Atividade.de(item) for item in (valor or [])]
        if not lista:
            raise ValidacaoErro("Informe ao menos uma brincadeira prevista.")
        self._atividades = lista

    @property
    def valor_combinado(self) -> Decimal:
        return self._valor_combinado

    @valor_combinado.setter
    def valor_combinado(self, valor) -> None:
        novo = para_decimal(valor, "valor combinado")
        if novo <= 0:
            raise ValidacaoErro("O valor combinado precisa ser maior que zero.")
        if novo < self.total_recebido:
            raise ValidacaoErro("O valor combinado não pode ficar abaixo do total já recebido.")
        self._valor_combinado = novo

    @property
    def detalhes(self) -> DetalhesComplementares:
        return self._detalhes

    @detalhes.setter
    def detalhes(self, valor: DetalhesComplementares) -> None:
        if not isinstance(valor, DetalhesComplementares):
            raise ValidacaoErro("Informe os detalhes complementares (brinde e deslocamento).")
        self._detalhes = valor

    @property
    def situacao(self) -> SituacaoFesta:
        return self._situacao

    @property
    def data_confirmacao(self) -> date:
        return self._data_confirmacao

    @property
    def confirmada(self) -> bool:
        """True enquanto a festa está confirmada (ainda não realizada/cancelada)."""
        return self._situacao is SituacaoFesta.CONFIRMADA

    @property
    def recreadores(self) -> Tuple[Recreador, ...]:
        return tuple(self._recreadores)

    def adicionar_recreador(self, recreador: Recreador) -> None:
        self._exigir_confirmada("alterar a equipe")
        if not isinstance(recreador, Recreador):
            raise ValidacaoErro("Recreador inválido.")
        if recreador in self._recreadores:
            raise RegraDeNegocioErro(f"{recreador.identificacao} já está escalado(a) nesta festa.")
        self._recreadores.append(recreador)

    def remover_recreador(self, recreador: Recreador) -> None:
        self._exigir_confirmada("alterar a equipe")
        if recreador not in self._recreadores:
            raise RegraDeNegocioErro(f"{recreador.identificacao} não está escalado(a) nesta festa.")
        self._recreadores.remove(recreador)

    @property
    def pagamentos(self) -> Tuple[RegistroPagamento, ...]:
        return tuple(self._pagamentos)

    @property
    def entrada_prevista(self) -> Decimal:
        """50% do valor combinado (R$ 1.000,00 -> R$ 500,00)."""
        return (self._valor_combinado * self.PERCENTUAL_ENTRADA).quantize(
            CENTAVOS, rounding=ROUND_HALF_UP
        )

    @property
    def total_recebido(self) -> Decimal:
        return sum((p.valor_recebido for p in self._pagamentos), _ZERO)

    @property
    def saldo_pendente(self) -> Decimal:
        """Valor combinado menos pagamentos recebidos (nunca diverge: CS-05)."""
        return self._valor_combinado - self.total_recebido

    @property
    def entrada_paga(self) -> bool:
        return self.total_recebido >= self.entrada_prevista

    @property
    def data_reservada(self) -> bool:
        """RN-02: a data só fica reservada depois que a entrada é paga."""
        return self._situacao is not SituacaoFesta.CANCELADA and self.entrada_paga

    def registrar_pagamento(self, valor, data_pagamento=None) -> RegistroPagamento:
        """Registra um pagamento recebido (informativo; não processa cobrança)."""
        if self._situacao is SituacaoFesta.CANCELADA:
            raise TransicaoInvalidaErro("Festa cancelada não aceita novos pagamentos.")
        valor = para_decimal(valor, "valor do pagamento")
        if valor <= 0:
            raise ValidacaoErro("O valor do pagamento precisa ser maior que zero.")
        saldo = self.saldo_pendente
        if valor > saldo:
            raise ValidacaoErro(
                f"O valor informado ({moeda(valor)}) é maior que o saldo pendente ({moeda(saldo)})."
            )
        registro = RegistroPagamento(valor, data_pagamento or date.today(), saldo - valor)
        self._pagamentos.append(registro)
        self._quitar_se_possivel()
        return registro

    def _quitar_se_possivel(self) -> None:
        if self._situacao is SituacaoFesta.REALIZADA and self.saldo_pendente == _ZERO:
            self._situacao = SituacaoFesta.QUITADA

    @property
    def lembretes(self) -> Tuple[Lembrete, ...]:
        return tuple(self._lembretes)

    def adicionar_lembrete(self, lembrete: Lembrete) -> None:
        if not isinstance(lembrete, Lembrete):
            raise ValidacaoErro("Lembrete inválido.")
        self._lembretes.append(lembrete)

    def _exigir_transicao(self, destino: SituacaoFesta) -> None:
        if destino not in self._TRANSICOES[self._situacao]:
            raise TransicaoInvalidaErro(
                f"Não é possível mudar a festa de '{self._situacao.value}' para '{destino.value}'."
            )

    def _exigir_confirmada(self, acao: str) -> None:
        if self._situacao is not SituacaoFesta.CONFIRMADA:
            raise TransicaoInvalidaErro(
                f"Só é possível {acao} em festas confirmadas (esta está {self._situacao.value})."
            )

    def marcar_realizada(self, hoje: Optional[date] = None) -> None:
        self._exigir_transicao(SituacaoFesta.REALIZADA)
        if self._data > (hoje or date.today()):
            raise RegraDeNegocioErro("Não é possível marcar como realizada uma festa com data futura.")
        self._situacao = SituacaoFesta.REALIZADA
        self._quitar_se_possivel()

    def cancelar(self, data_cancelamento=None) -> None:
        """RN-03: o valor já pago fica retido e pode ser usado em até 1 ano."""
        self._exigir_transicao(SituacaoFesta.CANCELADA)
        dia = para_data(data_cancelamento) if data_cancelamento else date.today()
        self._situacao = SituacaoFesta.CANCELADA
        self._data_cancelamento = dia
        self._credito_retido = self.total_recebido
        self._credito_valido_ate = somar_um_ano(dia) if self._credito_retido > 0 else None
        for lembrete in self._lembretes:
            lembrete.cancelar()

    def remarcar(self, nova_data, inicio=None, termino=None) -> None:
        """RN-04: a nova data é combinada caso a caso; o sistema só registra."""
        self._exigir_confirmada("remarcar")
        data = para_data(nova_data, "nova data")
        novo_inicio = para_hora(inicio, "horário de início") if inicio is not None else self._inicio
        novo_termino = (
            para_hora(termino, "horário de término") if termino is not None else self._termino
        )
        if novo_termino <= novo_inicio:
            raise ValidacaoErro("O horário de término precisa ser depois do horário de início.")
        self._data, self._inicio, self._termino = data, novo_inicio, novo_termino

    @property
    def data_cancelamento(self) -> Optional[date]:
        return self._data_cancelamento

    @property
    def credito_retido(self) -> Decimal:
        return self._credito_retido

    @property
    def credito_valido_ate(self) -> Optional[date]:
        return self._credito_valido_ate

    def atividades_fora_da_faixa(self) -> List[Atividade]:
        """Atividades com indicação etária que não cobre a faixa da festa."""
        return [a for a in self._atividades if not a.adequada_para(self._faixa_etaria)]

    def para_dicionario(self) -> dict:
        if self._contratante.id is None:
            raise ValidacaoErro("O contratante da festa ainda não foi cadastrado.")
        return {
            "id": self.id,
            "contratante_id": self._contratante.id,
            "data": self._data.isoformat(),
            "inicio": self._inicio.strftime("%H:%M"),
            "termino": self._termino.strftime("%H:%M"),
            "endereco": self._endereco,
            "quantidade_criancas": self._quantidade_criancas,
            "faixa_etaria": self._faixa_etaria.para_dicionario(),
            "atividades": [a.para_dicionario() for a in self._atividades],
            "valor_combinado": str(self._valor_combinado),
            "situacao": self._situacao.value,
            "data_confirmacao": self._data_confirmacao.isoformat(),
            "recreadores_ids": [r.id for r in self._recreadores],
            "pagamentos": [p.para_dicionario() for p in self._pagamentos],
            "lembretes": [l.para_dicionario() for l in self._lembretes],
            "detalhes": self._detalhes.para_dicionario(),
            "data_cancelamento": self._data_cancelamento.isoformat() if self._data_cancelamento else None,
            "credito_retido": str(self._credito_retido),
            "credito_valido_ate": self._credito_valido_ate.isoformat() if self._credito_valido_ate else None,
        }

    @classmethod
    def de_dicionario(cls, dados: Mapping[str, Any], contexto: Optional[Mapping[str, Any]] = None):
        contexto = contexto or {}
        contratantes = contexto.get("contratantes", {})
        recreadores = contexto.get("recreadores", {})
        contratante = contratantes.get(dados["contratante_id"])
        if contratante is None:
            raise ValidacaoErro(f"Contratante {dados['contratante_id']} não encontrado nos dados.")
        festa = cls(
            contratante=contratante,
            data=dados["data"],
            inicio=dados["inicio"],
            termino=dados["termino"],
            endereco=dados["endereco"],
            quantidade_criancas=dados["quantidade_criancas"],
            faixa_etaria=dados["faixa_etaria"],
            valor_combinado=dados["valor_combinado"],
            atividades=[Atividade.de_dicionario(a) for a in dados["atividades"]],
            detalhes=DetalhesComplementares.de_dicionario(dados["detalhes"]),
            data_confirmacao=dados.get("data_confirmacao"),
            id=dados.get("id"),
        )
        for rid in dados.get("recreadores_ids", []):
            recreador = recreadores.get(rid)
            if recreador is None:
                raise ValidacaoErro(f"Recreador {rid} não encontrado nos dados.")
            festa._recreadores.append(recreador)
        festa._pagamentos = [RegistroPagamento.de_dicionario(p) for p in dados.get("pagamentos", [])]
        festa._lembretes = [Lembrete.de_dicionario(l) for l in dados.get("lembretes", [])]
        festa._situacao = SituacaoFesta(dados.get("situacao", "confirmada"))
        if dados.get("data_cancelamento"):
            festa._data_cancelamento = para_data(dados["data_cancelamento"])
        festa._credito_retido = para_decimal(dados.get("credito_retido", "0"), "crédito retido")
        if dados.get("credito_valido_ate"):
            festa._credito_valido_ate = para_data(dados["credito_valido_ate"])
        return festa

    def __str__(self) -> str:
        numero = f"#{self.id}" if self.id is not None else "(nova)"
        return (
            f"Festa {numero} — {self._data:%d/%m/%Y} {self._inicio:%H:%M}–{self._termino:%H:%M} — "
            f"{self._contratante.nome} [{self._situacao.value}]"
        )

    def __repr__(self) -> str:
        return (
            f"Festa(id={self.id!r}, data={self._data.isoformat()!r}, "
            f"contratante={self._contratante.nome!r}, situacao={self._situacao.value!r})"
        )

    def __lt__(self, outra) -> bool:
        if not isinstance(outra, Festa):
            return NotImplemented
        return (self._data, self._inicio) < (outra._data, outra._inicio)

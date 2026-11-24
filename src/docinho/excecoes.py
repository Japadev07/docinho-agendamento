"""Exceções do domínio do sistema Docinho."""

from __future__ import annotations


class DocinhoErro(Exception):
    """Erro base do sistema."""


class ValidacaoErro(DocinhoErro):
    """Dado informado é inválido (formato, faixa de valores, tipo)."""


class CampoObrigatorioErro(ValidacaoErro):
    """Faltam campos obrigatórios no cadastro (RF-02)."""

    def __init__(self, campos):
        self.campos = list(campos)
        lista = ", ".join(self.campos)
        super().__init__(f"Campos obrigatórios não preenchidos: {lista}.")


class RegraDeNegocioErro(DocinhoErro):
    """Uma regra de negócio (RN-xx) impede a operação."""


class TransicaoInvalidaErro(RegraDeNegocioErro):
    """Mudança de situação da festa não permitida."""


class ConflitoEscalaErro(RegraDeNegocioErro):
    """Alocação de recreador gera conflito. A decisão final é da gestora (RF-04)."""

    def __init__(self, conflitos):
        self.conflitos = list(conflitos)
        detalhes = " | ".join(str(c) for c in self.conflitos)
        super().__init__(f"Conflito na escala: {detalhes}")


class NaoEncontradoErro(DocinhoErro):
    """Registro não localizado."""


class PersistenciaErro(DocinhoErro):
    """Falha ao gravar ou ler os dados."""

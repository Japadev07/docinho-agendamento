from __future__ import annotations


class DocinhoErro(Exception):
    pass


class ValidacaoErro(DocinhoErro):
    pass


class CampoObrigatorioErro(ValidacaoErro):
    def __init__(self, campos):
        self.campos = list(campos)
        lista = ", ".join(self.campos)
        super().__init__(f"Campos obrigatórios não preenchidos: {lista}.")


class RegraDeNegocioErro(DocinhoErro):
    pass


class TransicaoInvalidaErro(RegraDeNegocioErro):
    pass


class ConflitoEscalaErro(RegraDeNegocioErro):
    def __init__(self, conflitos):
        self.conflitos = list(conflitos)
        detalhes = " | ".join(str(c) for c in self.conflitos)
        super().__init__(f"Conflito na escala: {detalhes}")


class NaoEncontradoErro(DocinhoErro):
    pass


class PersistenciaErro(DocinhoErro):
    pass

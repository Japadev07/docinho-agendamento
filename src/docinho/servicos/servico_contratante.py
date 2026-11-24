from __future__ import annotations

from typing import List, Optional

from ..excecoes import RegraDeNegocioErro, ValidacaoErro
from ..modelos import Contratante
from ..persistencia import Armazenamento
from ..validacao import sem_acentos, somente_digitos


class ServicoContratante:
    def __init__(self, armazenamento: Armazenamento):
        self._arm = armazenamento

    def cadastrar(self, nome: str, telefone: str) -> Contratante:
        novo = Contratante(nome, telefone)
        if any(c == novo for c in self._arm.contratantes.values()):
            raise RegraDeNegocioErro("Já existe um contratante cadastrado com este telefone.")
        with self._arm.transacao():
            self._arm.adicionar_contratante(novo)
        return novo

    def obter(self, contratante_id: int) -> Contratante:
        return self._arm.obter_contratante(contratante_id)

    def listar(self) -> List[Contratante]:
        return sorted(self._arm.contratantes.values(), key=lambda c: sem_acentos(c.nome))

    def buscar(self, termo: str) -> List[Contratante]:
        if not isinstance(termo, str) or not termo.strip():
            raise ValidacaoErro("Informe um nome ou telefone para buscar.")
        termo_nome = sem_acentos(termo.strip())
        termo_digitos = somente_digitos(termo)
        encontrados = []
        for contratante in self._arm.contratantes.values():
            por_nome = termo_nome in sem_acentos(contratante.nome)
            por_telefone = bool(termo_digitos) and termo_digitos in contratante.telefone
            if por_nome or por_telefone:
                encontrados.append(contratante)
        return sorted(encontrados, key=lambda c: sem_acentos(c.nome))

    def atualizar(
        self, contratante_id: int, nome: Optional[str] = None, telefone: Optional[str] = None
    ) -> Contratante:
        contratante = self._arm.obter_contratante(contratante_id)
        teste = Contratante(nome if nome is not None else contratante.nome,
                            telefone if telefone is not None else contratante.telefone)
        for outro in self._arm.contratantes.values():
            if outro.id != contratante.id and outro == teste:
                raise RegraDeNegocioErro("Já existe um contratante cadastrado com este telefone.")
        with self._arm.transacao():
            contratante.nome = teste.nome
            contratante.telefone = teste.telefone
        return contratante

    def remover(self, contratante_id: int) -> None:
        contratante = self._arm.obter_contratante(contratante_id)
        if any(f.contratante.id == contratante.id for f in self._arm.festas.values()):
            raise RegraDeNegocioErro(
                "Este contratante possui festas registradas e não pode ser excluído."
            )
        with self._arm.transacao():
            del self._arm.contratantes[contratante.id]

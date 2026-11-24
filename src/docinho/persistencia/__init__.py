"""Persistência de dados (JSON ou memória)."""

from .armazenamento import Armazenamento
from .repositorio import Repositorio, RepositorioJSON, RepositorioMemoria

__all__ = ["Armazenamento", "Repositorio", "RepositorioJSON", "RepositorioMemoria"]

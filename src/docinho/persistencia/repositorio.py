"""Repositórios de persistência (JSON em arquivo e em memória)."""

from __future__ import annotations

import copy
import json
import os
import shutil
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, List, Optional, Union

from ..excecoes import PersistenciaErro

_FORMATO_BACKUP = "%Y%m%d_%H%M%S"


class Repositorio(ABC):
    """Contrato de armazenamento: lê e grava o estado completo do sistema."""

    @abstractmethod
    def carregar(self) -> dict:
        """Devolve o estado salvo ({} quando ainda não existe nada)."""

    @abstractmethod
    def salvar(self, dados: dict) -> None:
        """Grava o estado completo."""


class RepositorioMemoria(Repositorio):
    """Mantém os dados só em memória (testes e demonstrações)."""

    def __init__(self, dados: Optional[dict] = None):
        self._dados = copy.deepcopy(dados) if dados else {}

    def carregar(self) -> dict:
        return copy.deepcopy(self._dados)

    def salvar(self, dados: dict) -> None:
        self._dados = copy.deepcopy(dados)


class RepositorioJSON(Repositorio):
    """Persistência em arquivo JSON, com backup e restauração."""

    def __init__(
        self,
        caminho: Union[str, Path],
        pasta_backup: Union[str, Path, None] = None,
        agora: Optional[Callable[[], datetime]] = None,
    ):
        self.caminho = Path(caminho)
        self.pasta_backup = Path(pasta_backup) if pasta_backup else self.caminho.parent / "backups"
        self._agora = agora or datetime.now

    def carregar(self) -> dict:
        if not self.caminho.exists():
            return {}
        try:
            with open(self.caminho, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
        except (OSError, json.JSONDecodeError) as erro:
            raise PersistenciaErro(
                f"Não foi possível ler '{self.caminho.name}': {erro}. "
                "Use a restauração da última cópia de segurança, se houver."
            ) from erro
        if not isinstance(dados, dict):
            raise PersistenciaErro(f"O arquivo '{self.caminho.name}' não tem o formato esperado.")
        return dados

    def salvar(self, dados: dict) -> None:
        self._gravar_atomico(self.caminho, dados)

    @staticmethod
    def _gravar_atomico(destino: Path, dados: dict) -> None:
        temporario = destino.with_name(destino.name + ".tmp")
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            with open(temporario, "w", encoding="utf-8") as arquivo:
                json.dump(dados, arquivo, ensure_ascii=False, indent=2)
                arquivo.flush()
                os.fsync(arquivo.fileno())
            os.replace(temporario, destino)
        except (OSError, TypeError, ValueError) as erro:
            try:
                temporario.unlink()
            except OSError:
                pass
            raise PersistenciaErro(f"Falha ao gravar '{destino.name}': {erro}") from erro

    def _backups(self) -> List[Path]:
        if not self.pasta_backup.exists():
            return []
        return sorted(self.pasta_backup.glob("docinho_*.json"), reverse=True)

    def criar_backup(self) -> Path:
        """Copia o arquivo atual para a pasta de backups, com data e hora no nome."""
        if not self.caminho.exists():
            raise PersistenciaErro("Não há dados salvos para copiar.")
        try:
            self.pasta_backup.mkdir(parents=True, exist_ok=True)
            destino = self.pasta_backup / f"docinho_{self._agora().strftime(_FORMATO_BACKUP)}.json"
            shutil.copy2(self.caminho, destino)
        except OSError as erro:
            raise PersistenciaErro(f"Falha ao criar a cópia de segurança: {erro}") from erro
        return destino

    def backup_necessario(self, max_horas: int = 24) -> bool:
        """True quando não há backup ou o mais recente tem mais de ``max_horas``."""
        backups = self._backups()
        if not backups:
            return True
        try:
            ultimo = datetime.strptime(backups[0].stem.replace("docinho_", ""), _FORMATO_BACKUP)
        except ValueError:
            return True
        return self._agora() - ultimo >= timedelta(hours=max_horas)

    def restaurar_ultimo_backup(self) -> Path:
        """Restaura a cópia válida mais recente (testa se o JSON abre)."""
        for candidato in self._backups():
            try:
                with open(candidato, "r", encoding="utf-8") as arquivo:
                    dados = json.load(arquivo)
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(dados, dict):
                self._gravar_atomico(self.caminho, dados)
                return candidato
        raise PersistenciaErro("Nenhuma cópia de segurança válida foi encontrada.")

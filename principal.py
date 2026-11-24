"""Atalho para executar o sistema sem instalar o pacote: python principal.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from docinho.menu import principal  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(principal())

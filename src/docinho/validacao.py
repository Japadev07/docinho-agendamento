"""Funções de validação e conversão usadas pelos modelos e serviços."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .excecoes import ValidacaoErro

CENTAVOS = Decimal("0.01")


def texto_obrigatorio(valor, campo: str) -> str:
    """Retorna o texto sem espaços sobrando; falha se vazio ou não for texto."""
    if not isinstance(valor, str) or not valor.strip():
        raise ValidacaoErro(f"O campo '{campo}' é obrigatório.")
    return " ".join(valor.split())


def sem_acentos(texto: str) -> str:
    """Remove acentos e converte para minúsculas (comparação de buscas)."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c)).casefold()


def somente_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def normalizar_telefone(valor) -> str:
    """Aceita '(99) 98123-4567', '+55 99 98123-4567' etc. e devolve só os dígitos com DDD (10 ou 11 dígitos)."""
    if not isinstance(valor, str) or not valor.strip():
        raise ValidacaoErro("O campo 'telefone' é obrigatório.")
    digitos = somente_digitos(valor)
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    if len(digitos) not in (10, 11):
        raise ValidacaoErro(
            "Telefone inválido: informe DDD e número (10 ou 11 dígitos)."
        )
    return digitos


def formatar_telefone(digitos: str) -> str:
    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"


def para_decimal(valor, campo: str = "valor") -> Decimal:
    """Converte para Decimal com 2 casas. Aceita '1.000,50', '1000.50', int e Decimal."""
    if isinstance(valor, bool) or valor is None:
        raise ValidacaoErro(f"O campo '{campo}' é obrigatório.")
    try:
        if isinstance(valor, str):
            texto = valor.replace("R$", "").strip()
            if "," in texto:
                texto = texto.replace(".", "").replace(",", ".")
            numero = Decimal(texto)
        elif isinstance(valor, float):
            numero = Decimal(str(valor))
        else:
            numero = Decimal(valor)
    except (InvalidOperation, ValueError, TypeError):
        raise ValidacaoErro(f"O campo '{campo}' precisa ser um valor em reais válido.")
    if not numero.is_finite():
        raise ValidacaoErro(f"O campo '{campo}' precisa ser um valor em reais válido.")
    return numero.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def para_data(valor, campo: str = "data") -> date:
    """Aceita date, 'AAAA-MM-DD' ou 'DD/MM/AAAA'."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        texto = valor.strip()
        for formato in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(texto, formato).date()
            except ValueError:
                continue
    raise ValidacaoErro(f"O campo '{campo}' precisa ser uma data válida (DD/MM/AAAA).")


def para_hora(valor, campo: str = "horário") -> time:
    """Aceita time ou 'HH:MM'."""
    if isinstance(valor, datetime):
        return valor.time().replace(second=0, microsecond=0)
    if isinstance(valor, time):
        return valor.replace(second=0, microsecond=0)
    if isinstance(valor, str):
        try:
            return datetime.strptime(valor.strip(), "%H:%M").time()
        except ValueError:
            pass
    raise ValidacaoErro(f"O campo '{campo}' precisa ser um horário válido (HH:MM).")


def inteiro_positivo(valor, campo: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise ValidacaoErro(f"O campo '{campo}' precisa ser um número inteiro maior que zero.")
    return valor


def somar_um_ano(data: date) -> date:
    """Mesma data no ano seguinte (29/02 vira 28/02 em ano não bissexto). RN-03."""
    try:
        return data.replace(year=data.year + 1)
    except ValueError:
        return data.replace(year=data.year + 1, day=28)


def moeda(valor) -> str:
    """Formata em reais no padrão brasileiro: R$ 1.000,00."""
    numero = para_decimal(valor, "valor")
    texto = f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"

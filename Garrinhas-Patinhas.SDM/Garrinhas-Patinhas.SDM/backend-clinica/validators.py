import re
import datetime as dt


def so_digitos(v):
    return re.sub(r"\D", "", str(v or ""))


def cpf_valido(cpf):
    c = so_digitos(cpf)
    if len(c) != 11 or c == c[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(c[i]) * (n + 1 - i) for i in range(n))
        dv = (soma * 10) % 11
        if (0 if dv == 10 else dv) != int(c[n]):
            return False
    return True


def email_valido(e):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(e or "")))


def data_iso(v):
    """Aceita 'YYYY-MM-DD' ou 'YYYY-MM-DDTHH:MM[:SS]'. Retorna date/datetime ou None."""
    try:
        s = str(v)
        return dt.datetime.fromisoformat(s) if "T" in s or " " in s else dt.date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def microchip_valido(m):
    return bool(re.fullmatch(r"\d{15}", str(m or "")))   # padrão ISO 11784/11785 (15 dígitos)

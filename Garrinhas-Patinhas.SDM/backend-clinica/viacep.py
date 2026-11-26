"""Cliente da API pública ViaCEP (https://viacep.com.br)."""
import requests
import config
from validators import so_digitos


class CepInvalido(Exception):
    pass


class CepNaoEncontrado(Exception):
    pass


class ViaCepIndisponivel(Exception):
    def __init__(self, msg, timeout=False):
        super().__init__(msg)
        self.timeout = timeout


def consultar(cep):
    cep = so_digitos(cep)
    if len(cep) != 8:
        raise CepInvalido("CEP deve conter 8 dígitos.")
    try:
        r = requests.get(f"{config.VIACEP_URL.rstrip('/')}/{cep}/json/", timeout=config.VIACEP_TIMEOUT)
    except requests.Timeout:
        raise ViaCepIndisponivel("Tempo esgotado ao consultar o ViaCEP.", timeout=True)
    except requests.RequestException:
        raise ViaCepIndisponivel("Serviço ViaCEP indisponível.")
    if r.status_code == 400:
        raise CepInvalido("CEP em formato inválido.")
    if r.status_code != 200:
        raise ViaCepIndisponivel(f"ViaCEP respondeu HTTP {r.status_code}.")
    try:
        d = r.json()
    except ValueError:
        raise ViaCepIndisponivel("Resposta inválida do ViaCEP.")
    if d.get("erro") in (True, "true"):
        raise CepNaoEncontrado("CEP não encontrado.")
    return {"cep": cep, "logradouro": d.get("logradouro", ""), "complemento": d.get("complemento", ""),
            "bairro": d.get("bairro", ""), "cidade": d.get("localidade", ""), "uf": d.get("uf", ""),
            "codigo_ibge": d.get("ibge", "")}

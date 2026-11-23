"""ViaCEP FALSO, só para testes offline. O sistema real usa https://viacep.com.br/ws"""
import os, re, time
from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/ws/<cep>/json/")
def cep(cep):
    if not re.fullmatch(r"\d{8}", cep):
        return "Bad Request", 400
    if cep == "20040020":
        return jsonify({"cep": "20040-020", "logradouro": "Rua da Assembleia", "complemento": "", "bairro": "Centro",
                        "localidade": "Rio de Janeiro", "uf": "RJ", "ibge": "3304557"})
    if cep == "11111111":                     # simula lentidão => timeout no cliente
        time.sleep(4)
    return jsonify({"erro": "true"})          # CEP inexistente (formato real do ViaCEP)


if __name__ == "__main__":
    app.run(port=int(os.getenv("MOCK_VIACEP_PORT", "18099")))

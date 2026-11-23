import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "..", ".env"))

SQL_DIR = os.path.join(BASE_DIR, "..", "database", "clinica")
DB_PATH = os.getenv("CLINICA_DB", os.path.join(BASE_DIR, "clinica.db"))
PORT = int(os.getenv("CLINICA_PORT", "8080"))

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-trocar-em-producao-0123456789")
JWT_EXPIRATION_MIN = int(os.getenv("JWT_EXPIRATION_MIN", "120"))

VIACEP_URL = os.getenv("VIACEP_URL", "https://viacep.com.br/ws")
VIACEP_TIMEOUT = float(os.getenv("VIACEP_TIMEOUT_S", "3"))

GOVERNO_API_URL = os.getenv("GOVERNO_API_URL", "http://localhost:8081")
GOVERNO_API_KEY = os.getenv("GOVERNO_API_KEY", "chave-demo-governo")
INTEGRACAO_TIMEOUT = float(os.getenv("INTEGRACAO_TIMEOUT_S", "3"))
INTEGRACAO_MAX_TENTATIVAS = int(os.getenv("INTEGRACAO_MAX_TENTATIVAS", "5"))
REENVIO_AUTOMATICO_S = int(os.getenv("REENVIO_AUTOMATICO_S", "30"))  # 0 = desligado

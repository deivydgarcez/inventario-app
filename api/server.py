"""
Entry point do servidor — funciona tanto rodando com 'python server.py'
quanto como executável gerado pelo PyInstaller.
"""
import os
import sys

# Quando frozen (PyInstaller), BASE_DIR = pasta do .exe
# Quando script, BASE_DIR = pasta do server.py
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    # Garante que _MEIPASS está no path para importar main.py e app/
    if sys._MEIPASS not in sys.path:
        sys.path.insert(0, sys._MEIPASS)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Carrega .env da pasta do executável (substituindo vars de ambiente existentes)
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)

from app.licenca import validar_licenca
try:
    info = validar_licenca()
    print(f"[Invec] Licenca valida")
    print(f"[Invec] Cliente  : {info.get('cliente', '-')}")
    print(f"[Invec] CNPJ     : {info.get('cnpj', '-')}")
    expira = info.get("expira_em") or "Permanente"
    print(f"[Invec] Expira em: {expira}")
except RuntimeError as e:
    print()
    print("=" * 55)
    print("[Invec] ERRO DE LICENCA")
    print()
    for linha in str(e).splitlines():
        print(f"  {linha}")
    print("=" * 55)
    print()
    sys.exit(1)

import uvicorn

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(
        'main:app',
        host='0.0.0.0',
        port=port,
        reload=False,
        log_level='info',
    )

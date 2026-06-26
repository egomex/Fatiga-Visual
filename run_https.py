"""
Servidor Django con HTTPS para Python 3.13
Uso: python run_https.py
"""
import os
import ssl
import sys
from pathlib import Path

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fatiga_visual.settings')

import django
django.setup()

from django.core.servers.basehttp import WSGIServer, WSGIRequestHandler
from django.core.wsgi import get_wsgi_application

BASE_DIR = Path(__file__).resolve().parent
CERT     = str(BASE_DIR / 'localhost+1.pem')
KEY      = str(BASE_DIR / 'localhost+1-key.pem')

if not Path(CERT).exists():
    print("ERROR: No se encontró localhost+1.pem")
    print("Ejecuta primero: mkcert localhost 127.0.0.1")
    sys.exit(1)

# Crear contexto SSL compatible con Python 3.13
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(certfile=CERT, keyfile=KEY)

# Levantar servidor
server = WSGIServer(('0.0.0.0', 8000), WSGIRequestHandler)
server.set_app(get_wsgi_application())
server.socket = ctx.wrap_socket(server.socket, server_side=True)

print("EyeGuard corriendo en https://localhost:8000")
print("Presiona CTRL+C para detener.")

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\nServidor detenido.")
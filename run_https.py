"""
EyeGuard — run_https.py
Servidor Django con HTTPS compatible con Python 3.13
Uso: python run_https.py
"""
import os
import ssl
import sys
import threading
from pathlib import Path
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fatiga_visual.settings')

import django
django.setup()

from django.core.wsgi import get_wsgi_application

BASE_DIR = Path(__file__).resolve().parent
CERT     = str(BASE_DIR / 'localhost+1.pem')
KEY      = str(BASE_DIR / 'localhost+1-key.pem')

if not Path(CERT).exists():
    print("ERROR: No se encontró localhost+1.pem")
    print("Ejecuta: .\\mkcert localhost 127.0.0.1")
    sys.exit(1)

# Handler que no muestra logs de cada request para ir más rápido
class SilentHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        # Solo mostrar errores, no cada GET/POST
        if args and str(args[1]) >= '400':
            print(f"[{args[1]}] {args[0]}")

class ThreadedWSGIServer(WSGIServer):
    """Servidor multi-hilo para manejar requests concurrentes sin bloquearse."""
    def process_request(self, request, client_address):
        t = threading.Thread(
            target=self.process_request_thread,
            args=(request, client_address)
        )
        t.daemon = True
        t.start()

    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)

# Contexto SSL
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(certfile=CERT, keyfile=KEY)

# Levantar servidor multi-hilo
server = ThreadedWSGIServer(('0.0.0.0', 8000), SilentHandler)
server.set_app(get_wsgi_application())
server.socket = ctx.wrap_socket(server.socket, server_side=True)

print("=" * 45)
print("  EyeGuard corriendo en https://localhost:8000")
print("  Servidor multi-hilo activo")
print("  Presiona CTRL+C para detener")
print("=" * 45)

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\nServidor detenido.")
    server.shutdown()
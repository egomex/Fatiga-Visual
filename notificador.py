"""
EyeGuard — notificador.py
Ventana flotante que aparece encima de todas las apps.
Lee directamente de la BD de Django sin necesitar sesión.
Uso: python notificador.py
"""
import os
import sys
import time
import threading
import tkinter as tk

# Configurar Django para acceder a la BD directamente
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fatiga_visual.settings')

import django
django.setup()

from django.utils import timezone
from core.models import HistorialAlerta, Usuario

# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────
INTERVALO_SEG  = 3
alertas_vistas = set()   # IDs de alertas ya mostradas


# ─────────────────────────────────────────
# VENTANA FLOTANTE
# ─────────────────────────────────────────
def mostrar_alerta(titulo, mensaje):
    def crear_ventana():
        root = tk.Tk()
        root.title("EyeGuard")
        root.attributes('-topmost', True)
        root.attributes('-alpha', 0.95)

        ancho, alto = 380, 180
        pw = root.winfo_screenwidth()
        ph = root.winfo_screenheight()
        root.geometry(f'{ancho}x{alto}+{pw-ancho-20}+{ph-alto-60}')

        bg  = '#0f1f3a'
        acc = '#38bdf8'
        txt = '#e2eaf6'
        mut = '#6b85a8'
        root.configure(bg=bg)

        frame = tk.Frame(root, bg=bg, padx=16, pady=12)
        frame.pack(fill='both', expand=True)

        header = tk.Frame(frame, bg=bg)
        header.pack(fill='x', pady=(0, 8))

        tk.Label(header, text="👁️ EyeGuard", bg=bg, fg=acc,
                 font=('Segoe UI', 11, 'bold')).pack(side='left')
        tk.Button(header, text='✕', bg=bg, fg=mut,
                  font=('Segoe UI', 10), bd=0, cursor='hand2',
                  command=root.destroy).pack(side='right')

        tk.Label(frame,
                 text=titulo.replace('👁️ EyeGuard — ', '').replace('⏱️ EyeGuard — ', ''),
                 bg=bg, fg=txt, font=('Segoe UI', 10, 'bold'),
                 wraplength=340, justify='left', anchor='w').pack(fill='x', pady=(0, 6))

        tk.Label(frame, text=mensaje, bg=bg, fg=mut,
                 font=('Segoe UI', 9), wraplength=340,
                 justify='left', anchor='w').pack(fill='x')

        root.after(10000, root.destroy)
        root.lift()
        root.focus_force()
        root.mainloop()

    threading.Thread(target=crear_ventana, daemon=True).start()
    print(f"[Notificador] ✓ {titulo}")


# ─────────────────────────────────────────
# REVISAR BD DIRECTAMENTE
# ─────────────────────────────────────────
def revisar_bd():
    desde   = timezone.now() - timezone.timedelta(seconds=INTERVALO_SEG + 1)
    alertas = HistorialAlerta.objects.filter(
        creado_en__gte=desde,
    ).select_related('usuario').order_by('-creado_en')[:10]

    for alerta in alertas:
        if alerta.id in alertas_vistas:
            continue
        alertas_vistas.add(alerta.id)

        if alerta.tipo == 'avanzado':
            titulo  = '👁️ EyeGuard — Fatiga visual detectada'
            mensaje = alerta.recomendacion_ia[:120] if alerta.recomendacion_ia else alerta.mensaje
        else:
            titulo  = f'⏱️ EyeGuard — {alerta.protocolo}'
            mensaje = alerta.mensaje

        mostrar_alerta(titulo, mensaje)


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print("=" * 50)
    print("  EyeGuard — Notificador activo")
    print("  Presiona CTRL+C para detener")
    print("=" * 50)

    mostrar_alerta("EyeGuard iniciado", "El sistema de monitoreo visual está activo.")

    while True:
        try:
            revisar_bd()
        except Exception as e:
            print(f"[Notificador] Error: {e}")
        time.sleep(INTERVALO_SEG)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Notificador] Detenido.")
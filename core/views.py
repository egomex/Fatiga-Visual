from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from .models import Usuario, HistorialAlerta, ConfiguracionAlerta

# ─────────────────────────────────────────────────────────────
# PROTOCOLOS PREDETERMINADOS (definidos en servidor)
# ─────────────────────────────────────────────────────────────
PROTOCOLOS = [
    {
        'id':          '20-20-20',
        'nombre':      'Regla 20-20-20',
        'intervalo':   20,
        'duracion':    1,        # minutos de descanso
        'mensaje':     'Mira a 6 metros de distancia durante 20 segundos.',
        'destacado':   True,
        'color':       'blue',
        'cada_label':  'Cada 20 min',
        'desc':        'Cada 20 minutos, mira a 20 pies (~6 m) de distancia durante 20 segundos. Reduce la fatiga muscular ocular de forma comprobada.',
    },
    {
        'id':          'pausa-5',
        'nombre':      'Pausa corta — 5 min/hora',
        'intervalo':   60,
        'duracion':    5,
        'mensaje':     'Tómate 5 minutos de descanso completo.',
        'destacado':   False,
        'color':       'blue',
        'cada_label':  'Cada 60 min',
        'desc':        'Descanso de 5 minutos por cada hora de trabajo continuo frente a pantalla.',
    },
    {
        'id':          'pomodoro',
        'nombre':      'Técnica Pomodoro ocular',
        'intervalo':   25,
        'duracion':    5,
        'mensaje':     'Descansa los ojos 5 minutos, parpadea despacio.',
        'destacado':   False,
        'color':       'violet',
        'cada_label':  'Cada 25 min',
        'desc':        'Adaptación del método Pomodoro: 25 minutos de trabajo, 5 de descanso visual.',
    },
    {
        'id':          'pausa-15',
        'nombre':      'Pausa larga — 15 min/2h',
        'intervalo':   120,
        'duracion':    15,
        'mensaje':     'Descansa 15 minutos, levántate y camina.',
        'destacado':   False,
        'color':       'green',
        'cada_label':  'Cada 120 min',
        'desc':        'Descanso de 15 minutos por cada dos horas de trabajo. Ideal para jornadas largas.',
    },
    {
        'id':          'oms',
        'nombre':      'Protocolo OMS',
        'intervalo':   45,
        'duracion':    10,
        'mensaje':     'Realiza una pausa activa de 10 minutos.',
        'destacado':   False,
        'color':       'orange',
        'cada_label':  'Cada 45 min',
        'desc':        'Basado en las guías de la OMS para el uso seguro de pantallas.',
    },
]


def _get_protocolo(pid):
    return next((p for p in PROTOCOLOS if p['id'] == pid), None)


# ─────────────────────────────────────────────────────────────
# INICIO — login / registro / bienvenida de regreso
# ─────────────────────────────────────────────────────────────
def inicio(request):
    """
    GET:
      - Si hay sesión activa → muestra pantalla "¿Continuar como X?"
      - Si no              → muestra formulario de login/registro
    POST action=continuar  → redirige al dashboard sin cambiar usuario
    POST action=cambiar    → limpia sesión, muestra form limpio
    POST action=login      → autentica o registra y abre sesión
    """
    # ── Acción: el usuario quiere continuar con su sesión guardada ──
    if request.method == 'POST' and request.POST.get('action') == 'continuar':
        return redirect('dashboard_basico')

    # ── Acción: el usuario quiere cambiar de cuenta ──
    if request.method == 'POST' and request.POST.get('action') == 'cambiar':
        request.session.flush()
        return redirect('inicio')

    # ── Acción: login / registro ──
    if request.method == 'POST' and request.POST.get('action') == 'login':
        nombre   = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        mode     = request.POST.get('mode', 'basic')
        errores  = {}

        if not nombre:
            errores['nombre'] = 'El nombre es obligatorio.'
        if not password:
            errores['password'] = 'La contraseña es obligatoria.'
        if len(password) < 4:
            errores['password'] = 'La contraseña debe tener al menos 4 caracteres.'

        if not errores:
            usuario = Usuario.objects.filter(nombre=nombre).first()

            if usuario:
                # Usuario existente → verificar contraseña
                if check_password(password, usuario.password):
                    request.session['usuario_id'] = usuario.pk
                    request.session['username']   = usuario.nombre
                    request.session['mode']       = mode
                    if mode == 'advanced':
                        return redirect('dashboard_avanzado')
                    return redirect('dashboard_basico')
                else:
                    errores['password'] = 'Contraseña incorrecta.'
            else:
                # Usuario nuevo → registrar
                nuevo = Usuario(nombre=nombre)
                nuevo.set_password(password)
                nuevo.save()
                request.session['usuario_id'] = nuevo.pk
                request.session['username']   = nuevo.nombre
                request.session['mode']       = mode
                if mode == 'advanced':
                    return redirect('dashboard_avanzado')
                return redirect('dashboard_basico')

        return render(request, 'index.html', {
            'errores': errores,
            'nombre_previo': nombre,
            'mode_previo':   mode,
        })

    # ── GET: ¿hay sesión activa? ──
    usuario_id = request.session.get('usuario_id')
    if usuario_id:
        try:
            usuario = Usuario.objects.get(pk=usuario_id)
            return render(request, 'index.html', {
                'sesion_activa': True,
                'username':      usuario.nombre,
            })
        except Usuario.DoesNotExist:
            request.session.flush()

    return render(request, 'index.html')


# ─────────────────────────────────────────────────────────────
# DASHBOARD BÁSICO — menú de las 3 secciones
# ─────────────────────────────────────────────────────────────
def dashboard_basico(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('inicio')
    try:
        usuario = Usuario.objects.get(pk=usuario_id)
    except Usuario.DoesNotExist:
        request.session.flush()
        return redirect('inicio')

    return render(request, 'dashboard_basico.html', {'usuario': usuario})


# ─────────────────────────────────────────────────────────────
# SECCIÓN 1 — ALERTAS PREDETERMINADAS
# ─────────────────────────────────────────────────────────────
def alertas_predeterminadas(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('inicio')
    usuario = Usuario.objects.get(pk=usuario_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        # ── Activar protocolo: guarda en sesión qué protocolo está activo ──
        if action == 'activar':
            pid = request.POST.get('protocolo_id')
            protocolo = _get_protocolo(pid)
            if protocolo:
                request.session['protocolo_activo'] = protocolo
                # Registrar inicio en historial
                HistorialAlerta.objects.create(
                    usuario   = usuario,
                    protocolo = protocolo['nombre'],
                    mensaje   = f"Protocolo iniciado — cada {protocolo['intervalo']} min",
                    tipo      = 'preset',
                    completada= False,
                )

        # ── Registrar alerta disparada (llamada desde el timer del navegador) ──
        elif action == 'alerta_disparada':
            pid = request.POST.get('protocolo_id')
            protocolo = _get_protocolo(pid)
            if protocolo:
                HistorialAlerta.objects.create(
                    usuario   = usuario,
                    protocolo = protocolo['nombre'],
                    mensaje   = protocolo['mensaje'],
                    tipo      = 'preset',
                    completada= False,
                )

        # ── Marcar descanso completado ──
        elif action == 'completar':
            alerta_id = request.POST.get('alerta_id')
            if alerta_id:
                HistorialAlerta.objects.filter(
                    pk=alerta_id, usuario=usuario
                ).update(completada=True)

        # ── Detener protocolo ──
        elif action == 'detener':
            pid = request.session.get('protocolo_activo', {}).get('id')
            protocolo = _get_protocolo(pid) if pid else None
            if protocolo:
                HistorialAlerta.objects.create(
                    usuario   = usuario,
                    protocolo = protocolo['nombre'],
                    mensaje   = 'Protocolo detenido por el usuario',
                    tipo      = 'preset',
                    completada= False,
                )
            request.session.pop('protocolo_activo', None)

        return redirect('alertas_predeterminadas')

    protocolo_activo = request.session.get('protocolo_activo')
    return render(request, 'alertas_predeterminadas.html', {
        'usuario':          usuario,
        'protocolos':       PROTOCOLOS,
        'protocolo_activo': protocolo_activo,
    })


# ─────────────────────────────────────────────────────────────
# SECCIÓN 2 — ALERTAS CONFIGURABLES
# ─────────────────────────────────────────────────────────────
def alertas_configurables(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('inicio')
    usuario = Usuario.objects.get(pk=usuario_id)

    # Cargar o crear configuración guardada del usuario
    config, _ = ConfiguracionAlerta.objects.get_or_create(usuario=usuario)

    if request.method == 'POST':
        action = request.POST.get('action')

        # ── Guardar y activar configuración ──
        if action == 'activar':
            intervalo = int(request.POST.get('intervalo_trabajo', 30))
            duracion  = int(request.POST.get('duracion_descanso', 5))
            mensaje   = request.POST.get('mensaje_custom', '').strip()
            sonido    = request.POST.get('sonido_activo') == 'on'

            # Validar rangos
            intervalo = max(5,  min(120, intervalo))
            duracion  = max(1,  min(30,  duracion))

            # Guardar en BD
            config.intervalo_trabajo  = intervalo
            config.duracion_descanso  = duracion
            config.mensaje_custom     = mensaje
            config.sonido_activo      = sonido
            config.save()

            # Guardar en sesión como protocolo activo configurable
            request.session['config_activa'] = {
                'intervalo': intervalo,
                'duracion':  duracion,
                'mensaje':   mensaje or f'Descansa {duracion} minuto{"s" if duracion > 1 else ""}.',
                'sonido':    sonido,
            }

            HistorialAlerta.objects.create(
                usuario   = usuario,
                protocolo = f'Personalizado ({intervalo} min)',
                mensaje   = f'Cada {intervalo} min — Descanso de {duracion} min',
                tipo      = 'custom',
                completada= False,
            )

        # ── Registrar alerta disparada ──
        elif action == 'alerta_disparada':
            cfg = request.session.get('config_activa', {})
            HistorialAlerta.objects.create(
                usuario   = usuario,
                protocolo = f"Personalizado ({cfg.get('intervalo', '?')} min)",
                mensaje   = cfg.get('mensaje', '¡Hora de descansar!'),
                tipo      = 'custom',
                completada= False,
            )

        # ── Marcar completado ──
        elif action == 'completar':
            alerta_id = request.POST.get('alerta_id')
            if alerta_id:
                HistorialAlerta.objects.filter(
                    pk=alerta_id, usuario=usuario
                ).update(completada=True)

        # ── Detener ──
        elif action == 'detener':
            cfg = request.session.get('config_activa')
            if cfg:
                HistorialAlerta.objects.create(
                    usuario   = usuario,
                    protocolo = f"Personalizado ({cfg.get('intervalo', '?')} min)",
                    mensaje   = 'Configuración detenida por el usuario',
                    tipo      = 'custom',
                    completada= False,
                )
            request.session.pop('config_activa', None)

        return redirect('alertas_configurables')

    config_activa = request.session.get('config_activa')
    return render(request, 'alertas_configurables.html', {
        'usuario':      usuario,
        'config':       config,
        'config_activa': config_activa,
    })


# ─────────────────────────────────────────────────────────────
# SECCIÓN 3 — HISTORIAL
# ─────────────────────────────────────────────────────────────
def historial(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('inicio')
    usuario = Usuario.objects.get(pk=usuario_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'limpiar':
            HistorialAlerta.objects.filter(usuario=usuario).delete()
        return redirect('historial')

    filtro   = request.GET.get('filtro', 'all')
    alertas  = HistorialAlerta.objects.filter(usuario=usuario)
    if filtro == 'preset':
        alertas = alertas.filter(tipo='preset')
    elif filtro == 'custom':
        alertas = alertas.filter(tipo='custom')

    total        = HistorialAlerta.objects.filter(usuario=usuario).count()
    completadas  = HistorialAlerta.objects.filter(usuario=usuario, completada=True).count()

    protocolo_activo = (
        request.session.get('protocolo_activo', {}).get('nombre')
        or (f"Personalizado ({request.session['config_activa']['intervalo']} min)"
            if request.session.get('config_activa') else '—')
    )

    return render(request, 'historial.html', {
        'usuario':          usuario,
        'alertas':          alertas,
        'filtro':           filtro,
        'total':            total,
        'completadas':      completadas,
        'protocolo_activo': protocolo_activo,
    })


# ─────────────────────────────────────────────────────────────
# CERRAR SESIÓN
# ─────────────────────────────────────────────────────────────
def cerrar_sesion(request):
    request.session.flush()
    return redirect('inicio')


# ─────────────────────────────────────────────────────────────
# PLACEHOLDER MODO AVANZADO
# ─────────────────────────────────────────────────────────────
def dashboard_avanzado(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('inicio')
    usuario = Usuario.objects.get(pk=usuario_id)
    return render(request, 'dashboard_avanzado.html', {'usuario': usuario})
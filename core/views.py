import json
import urllib.request
import urllib.error
try:
    import requests as req_lib
    USAR_REQUESTS = True
except ImportError:
    USAR_REQUESTS = False
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from .models import Usuario, HistorialAlerta, ConfiguracionAlerta, SesionAvanzada

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
# INICIO — login / registro / selector de modo
# ─────────────────────────────────────────────────────────────
def inicio(request):
    """
    Flujo:
      Sin sesión  → formulario login/registro
      Con sesión  → selector de modo (básico / avanzado) con opción de cerrar sesión
      Salir       → vuelve al selector de modo (sesión se mantiene)
      Cerrar sesión → limpia sesión y pide login de nuevo
    """
    # ── POST: elegir modo con sesión activa ──
    if request.method == 'POST' and request.POST.get('action') == 'elegir_modo':
        mode = request.POST.get('mode', 'basic')
        request.session['mode'] = mode
        if mode == 'advanced':
            return redirect('dashboard_avanzado')
        return redirect('dashboard_basico')

    # ── POST: login / registro ──
    if request.method == 'POST' and request.POST.get('action') == 'login':
        nombre   = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        mode     = request.POST.get('mode', 'basic')
        errores  = {}

        if not nombre:
            errores['nombre'] = 'El nombre es obligatorio.'
        if not password:
            errores['password'] = 'La contraseña es obligatoria.'
        elif len(password) < 4:
            errores['password'] = 'La contraseña debe tener al menos 4 caracteres.'

        if not errores:
            usuario = Usuario.objects.filter(nombre=nombre).first()
            if usuario:
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
            'errores':      errores,
            'nombre_previo': nombre,
            'mode_previo':  mode,
        })

    # ── GET: ¿hay sesión activa? ──
    usuario_id = request.session.get('usuario_id')
    if usuario_id:
        try:
            usuario = Usuario.objects.get(pk=usuario_id)
            return render(request, 'index.html', {
                'sesion_activa': True,
                'usuario':       usuario,
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
# SALIR — vuelve al selector de modo, sesión se mantiene
# ─────────────────────────────────────────────────────────────
def salir(request):
    return redirect('inicio')


# ─────────────────────────────────────────────────────────────
# CERRAR SESIÓN — limpia sesión completamente
# ─────────────────────────────────────────────────────────────
def cerrar_sesion(request):
    request.session.flush()
    return redirect('inicio')


# ─────────────────────────────────────────────────────────────
# MODO AVANZADO — helpers
# ─────────────────────────────────────────────────────────────

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def _llamar_groq(api_key, prompt):
    """
    Llama a la API de Groq (LLaMA 3) y devuelve el texto de respuesta.
    Usa requests si está disponible, si no urllib.
    """
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent":    "Mozilla/5.0 (compatible; EyeGuard/1.0)",
        "Accept":        "application/json",
    }
    payload = {
        "model":       "llama-3.3-70b-versatile",
        "messages":    [{"role": "user", "content": prompt}],
        "max_tokens":  300,
        "temperature": 0.7,
    }

    # Usar requests (más confiable con Cloudflare)
    if USAR_REQUESTS:
        try:
            resp = req_lib.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=15,
            )
            if resp.status_code == 200:
                print("[Groq] Respuesta OK")
                return resp.json()["choices"][0]["message"]["content"].strip()
            else:
                print(f"[Groq] HTTPError {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            print(f"[Groq] Error con requests: {e}")
            return None

    # Fallback: urllib
    body = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        GROQ_API_URL, data=body, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
            print("[Groq] Respuesta OK (urllib)")
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        print(f"[Groq] HTTPError {e.code}: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"[Groq] Error urllib: {e}")
        return None


def _build_prompt(usuario_nombre, ear, parpadeos, total_alertas_sesion):
    """Construye el prompt para Gemini con el contexto del usuario."""
    return (
        "Eres un asistente médico especialista en salud visual. "
        f"El usuario '{usuario_nombre}' lleva trabajando frente a la pantalla "
        "y su sistema de monitoreo detectó lo siguiente:\n"
        f"- EAR (Eye Aspect Ratio) promedio: {ear:.3f} "
        "(valores menores a 0.25 indican ojos casi cerrados)\n"
        f"- Parpadeos por minuto: {parpadeos} "
        "(lo normal es entre 12 y 20; más de 20 indica fatiga o irritación)\n"
        f"- Número de alertas de fatiga en esta sesión: {total_alertas_sesion}\n\n"
        "Con base en estos datos, proporciona:\n"
        "1. Un diagnóstico breve de la condición visual actual.\n"
        "2. Una recomendación concreta e inmediata (qué hacer ahora).\n"
        "3. Si los síntomas son preocupantes, indica si debe consultar a un médico.\n\n"
        "Responde en español, de forma clara y en máximo 3 párrafos cortos. "
        "No uses markdown, solo texto plano."
    )


def _get_usuario_avanzado(request):
    """Helper: valida sesión y retorna (usuario, None) o (None, redirect)."""
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return None, redirect('inicio')
    try:
        return Usuario.objects.get(pk=usuario_id), None
    except Usuario.DoesNotExist:
        request.session.flush()
        return None, redirect('inicio')


# ─────────────────────────────────────────────────────────────
# DASHBOARD AVANZADO — vista principal
# ─────────────────────────────────────────────────────────────
def dashboard_avanzado(request):
    usuario, err = _get_usuario_avanzado(request)
    if err:
        return err

    # Obtener o crear sesión avanzada activa
    sesion = SesionAvanzada.objects.filter(usuario=usuario, activa=True).first()

    # Historial de alertas avanzadas de la sesión actual
    alertas_sesion = []
    if sesion:
        alertas_sesion = HistorialAlerta.objects.filter(
            usuario=usuario,
            tipo='avanzado',
            creado_en__gte=sesion.inicio,
        ).order_by('-creado_en')[:20]

    # Últimas recomendaciones IA (para el panel de recomendaciones)
    recomendaciones = HistorialAlerta.objects.filter(
        usuario=usuario,
        tipo='avanzado',
    ).exclude(recomendacion_ia='').order_by('-creado_en')[:5]

    # Estadísticas globales del usuario en modo avanzado
    total_sesiones  = SesionAvanzada.objects.filter(usuario=usuario).count()
    total_alertas   = HistorialAlerta.objects.filter(usuario=usuario, tipo='avanzado').count()

    return render(request, 'dashboard_avanzado.html', {
        'usuario':         usuario,
        'sesion':          sesion,
        'alertas_sesion':  alertas_sesion,
        'recomendaciones': recomendaciones,
        'total_sesiones':  total_sesiones,
        'total_alertas':   total_alertas,
        'gemini_key_ok':   bool(usuario.gemini_api_key),
    })


# ─────────────────────────────────────────────────────────────
# GUARDAR API KEY DE GEMINI (POST desde el dashboard)
# ─────────────────────────────────────────────────────────────
def guardar_api_key(request):
    if request.method == 'POST':
        usuario, err = _get_usuario_avanzado(request)
        if err:
            return err
        key = request.POST.get('gemini_api_key', '').strip()
        if key:
            # Guardar en BD para que persista entre sesiones
            usuario.gemini_api_key = key
            usuario.save(update_fields=['gemini_api_key'])
    return redirect('dashboard_avanzado')


# ─────────────────────────────────────────────────────────────
# INICIAR SESIÓN AVANZADA
# ─────────────────────────────────────────────────────────────
def iniciar_sesion_avanzada(request):
    if request.method != 'POST':
        return redirect('dashboard_avanzado')

    usuario, err = _get_usuario_avanzado(request)
    if err:
        return err

    # Cerrar sesión activa anterior si existe
    SesionAvanzada.objects.filter(usuario=usuario, activa=True).update(activa=False)

    # Crear nueva sesión
    SesionAvanzada.objects.create(usuario=usuario)
    return redirect('dashboard_avanzado')


# ─────────────────────────────────────────────────────────────
# DETENER SESIÓN AVANZADA
# ─────────────────────────────────────────────────────────────
def detener_sesion_avanzada(request):
    if request.method != 'POST':
        return redirect('dashboard_avanzado')

    usuario, err = _get_usuario_avanzado(request)
    if err:
        return err

    sesion = SesionAvanzada.objects.filter(usuario=usuario, activa=True).first()
    if sesion:
        sesion.fin    = timezone.now()
        sesion.activa = False
        # Calcular promedios de la sesión
        alertas = HistorialAlerta.objects.filter(
            usuario=usuario, tipo='avanzado', creado_en__gte=sesion.inicio
        )
        ears = [a.ear_valor for a in alertas if a.ear_valor is not None]
        parps = [a.parpadeos_minuto for a in alertas if a.parpadeos_minuto is not None]
        sesion.total_alertas      = alertas.count()
        sesion.ear_promedio       = round(sum(ears) / len(ears), 3) if ears else None
        sesion.parpadeos_promedio = round(sum(parps) / len(parps), 1) if parps else None
        sesion.save()

    return redirect('dashboard_avanzado')


# ─────────────────────────────────────────────────────────────
# RECIBIR ALERTA DE FATIGA (fetch desde JS con datos de MediaPipe)
# ─────────────────────────────────────────────────────────────
@csrf_exempt
def registrar_fatiga(request):
    """
    Recibe via fetch (POST JSON) los datos de fatiga detectados por MediaPipe.
    Llama a Gemini, guarda la alerta en BD y devuelve la recomendación como JSON.
    """
    if request.method != 'POST':
        return _json_error('Método no permitido', 405)

    usuario, err = _get_usuario_avanzado(request)
    if err:
        return _json_error('Sesión inválida', 401)

    # Parsear datos enviados por JS
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return _json_error('JSON inválido', 400)

    ear         = float(data.get('ear', 0))
    parpadeos   = int(data.get('parpadeos_por_minuto', 0))
    motivo      = data.get('motivo', 'EAR bajo + parpadeo excesivo')

    # Sesión activa
    sesion = SesionAvanzada.objects.filter(usuario=usuario, activa=True).first()
    total_alertas_sesion = 0
    if sesion:
        total_alertas_sesion = HistorialAlerta.objects.filter(
            usuario=usuario, tipo='avanzado', creado_en__gte=sesion.inicio
        ).count()

    # Llamar a Gemini
    api_key = usuario.gemini_api_key or ''
    recomendacion = ''
    if api_key:
        prompt        = _build_prompt(usuario.nombre, ear, parpadeos, total_alertas_sesion + 1)
        recomendacion = _llamar_groq(api_key, prompt)
        if not recomendacion:
            recomendacion = (
                'No se pudo conectar con Gemini. '
                'Verifica que tu API Key sea válida y tengas conexión a internet.'
            )
    else:
        recomendacion = 'No hay API Key de Groq configurada. Ingresa tu clave en el banner amarillo.'

    # Guardar en BD
    alerta = HistorialAlerta.objects.create(
        usuario          = usuario,
        protocolo        = 'Detección de fatiga visual',
        mensaje          = motivo,
        tipo             = 'avanzado',
        completada       = False,
        ear_valor        = round(ear, 3),
        parpadeos_minuto = parpadeos,
        recomendacion_ia = recomendacion,
    )

    # Actualizar contador de sesión
    if sesion:
        sesion.total_alertas = total_alertas_sesion + 1
        sesion.save(update_fields=['total_alertas'])

    return JsonResponse({
        'ok':             True,
        'alerta_id':      alerta.pk,
        'recomendacion':  recomendacion,
        'ear':            ear,
        'parpadeos':      parpadeos,
        'hora':           alerta.creado_en.strftime('%H:%M'),
    })


# ─────────────────────────────────────────────────────────────
# HISTORIAL AVANZADO
# ─────────────────────────────────────────────────────────────
def historial_avanzado(request):
    usuario, err = _get_usuario_avanzado(request)
    if err:
        return err

    if request.method == 'POST' and request.POST.get('action') == 'limpiar':
        HistorialAlerta.objects.filter(usuario=usuario, tipo='avanzado').delete()
        return redirect('historial_avanzado')

    alertas = HistorialAlerta.objects.filter(usuario=usuario, tipo='avanzado')
    total   = alertas.count()
    con_recomendacion = alertas.exclude(recomendacion_ia='').count()

    return render(request, 'historial_avanzado.html', {
        'usuario':           usuario,
        'alertas':           alertas,
        'total':             total,
        'con_recomendacion': con_recomendacion,
    })


# ─────────────────────────────────────────────────────────────
# HELPER: respuesta JSON de error
# ─────────────────────────────────────────────────────────────
def _json_error(msg, status=400):
    return JsonResponse({'ok': False, 'error': msg}, status=status)
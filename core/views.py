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
        'duracion':    1,
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
    if request.method == 'POST' and request.POST.get('action') == 'elegir_modo':
        mode = request.POST.get('mode', 'basic')
        request.session['mode'] = mode
        if mode == 'advanced':
            return redirect('dashboard_avanzado')
        return redirect('dashboard_basico')

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
            'errores':       errores,
            'nombre_previo': nombre,
            'mode_previo':   mode,
        })

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
# DASHBOARD BÁSICO
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

        if action == 'activar':
            pid = request.POST.get('protocolo_id')
            protocolo = _get_protocolo(pid)
            if protocolo:
                request.session['protocolo_activo'] = protocolo
                HistorialAlerta.objects.create(
                    usuario   = usuario,
                    protocolo = protocolo['nombre'],
                    mensaje   = f"Protocolo iniciado — cada {protocolo['intervalo']} min",
                    tipo      = 'preset',
                    completada= False,
                )

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

        elif action == 'completar':
            alerta_id = request.POST.get('alerta_id')
            if alerta_id:
                HistorialAlerta.objects.filter(
                    pk=alerta_id, usuario=usuario
                ).update(completada=True)

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
    config, _ = ConfiguracionAlerta.objects.get_or_create(usuario=usuario)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'activar':
            intervalo = int(request.POST.get('intervalo_trabajo', 30))
            duracion  = int(request.POST.get('duracion_descanso', 5))
            mensaje   = request.POST.get('mensaje_custom', '').strip()
            sonido    = request.POST.get('sonido_activo') == 'on'
            intervalo = max(5, min(120, intervalo))
            duracion  = max(1, min(30,  duracion))
            config.intervalo_trabajo  = intervalo
            config.duracion_descanso  = duracion
            config.mensaje_custom     = mensaje
            config.sonido_activo      = sonido
            config.save()
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

        elif action == 'alerta_disparada':
            cfg = request.session.get('config_activa', {})
            HistorialAlerta.objects.create(
                usuario   = usuario,
                protocolo = f"Personalizado ({cfg.get('intervalo', '?')} min)",
                mensaje   = cfg.get('mensaje', '¡Hora de descansar!'),
                tipo      = 'custom',
                completada= False,
            )

        elif action == 'completar':
            alerta_id = request.POST.get('alerta_id')
            if alerta_id:
                HistorialAlerta.objects.filter(
                    pk=alerta_id, usuario=usuario
                ).update(completada=True)

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
        'usuario':       usuario,
        'config':        config,
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
        if request.POST.get('action') == 'limpiar':
            HistorialAlerta.objects.filter(usuario=usuario).delete()
        return redirect('historial')

    filtro  = request.GET.get('filtro', 'all')
    alertas = HistorialAlerta.objects.filter(usuario=usuario)
    if filtro == 'preset':
        alertas = alertas.filter(tipo='preset')
    elif filtro == 'custom':
        alertas = alertas.filter(tipo='custom')

    total       = HistorialAlerta.objects.filter(usuario=usuario).count()
    completadas = HistorialAlerta.objects.filter(usuario=usuario, completada=True).count()
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
# SALIR / CERRAR SESIÓN
# ─────────────────────────────────────────────────────────────
def salir(request):
    return redirect('inicio')


def cerrar_sesion(request):
    request.session.flush()
    return redirect('inicio')


# ─────────────────────────────────────────────────────────────
# GROQ API
# ─────────────────────────────────────────────────────────────
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def _llamar_groq(api_key, prompt):
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

    if USAR_REQUESTS:
        try:
            resp = req_lib.post(GROQ_API_URL, headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                print("[Groq] Respuesta OK")
                return resp.json()["choices"][0]["message"]["content"].strip()
            else:
                print(f"[Groq] HTTPError {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            print(f"[Groq] Error con requests: {e}")
            return None

    body = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(GROQ_API_URL, data=body, headers=headers, method="POST")
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
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return None, redirect('inicio')
    try:
        return Usuario.objects.get(pk=usuario_id), None
    except Usuario.DoesNotExist:
        request.session.flush()
        return None, redirect('inicio')


def _json_error(msg, status=400):
    return JsonResponse({'ok': False, 'error': msg}, status=status)


# ─────────────────────────────────────────────────────────────
# DASHBOARD AVANZADO
# ─────────────────────────────────────────────────────────────
def dashboard_avanzado(request):
    usuario, err = _get_usuario_avanzado(request)
    if err:
        return err

    sesion = SesionAvanzada.objects.filter(usuario=usuario, activa=True).first()
    alertas_sesion = []
    if sesion:
        alertas_sesion = HistorialAlerta.objects.filter(
            usuario=usuario,
            tipo='avanzado',
            creado_en__gte=sesion.inicio,
        ).order_by('-creado_en')[:20]

    recomendaciones = HistorialAlerta.objects.filter(
        usuario=usuario,
        tipo='avanzado',
    ).exclude(recomendacion_ia='').order_by('-creado_en')[:5]

    total_sesiones = SesionAvanzada.objects.filter(usuario=usuario).count()
    total_alertas  = HistorialAlerta.objects.filter(usuario=usuario, tipo='avanzado').count()

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
# GUARDAR API KEY
# ─────────────────────────────────────────────────────────────
def guardar_api_key(request):
    if request.method == 'POST':
        usuario, err = _get_usuario_avanzado(request)
        if err:
            return err
        key = request.POST.get('gemini_api_key', '').strip()
        if key:
            usuario.gemini_api_key = key
            usuario.save(update_fields=['gemini_api_key'])
    return redirect('dashboard_avanzado')


# ─────────────────────────────────────────────────────────────
# INICIAR / DETENER SESIÓN AVANZADA
# ─────────────────────────────────────────────────────────────
def iniciar_sesion_avanzada(request):
    if request.method != 'POST':
        return redirect('dashboard_avanzado')
    usuario, err = _get_usuario_avanzado(request)
    if err:
        return err
    SesionAvanzada.objects.filter(usuario=usuario, activa=True).update(activa=False)
    SesionAvanzada.objects.create(usuario=usuario)
    return redirect('dashboard_avanzado')


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
        alertas = HistorialAlerta.objects.filter(
            usuario=usuario, tipo='avanzado', creado_en__gte=sesion.inicio
        )
        ears  = [a.ear_valor for a in alertas if a.ear_valor is not None]
        parps = [a.parpadeos_minuto for a in alertas if a.parpadeos_minuto is not None]
        sesion.total_alertas      = alertas.count()
        sesion.ear_promedio       = round(sum(ears) / len(ears), 3) if ears else None
        sesion.parpadeos_promedio = round(sum(parps) / len(parps), 1) if parps else None
        sesion.save()
    return redirect('dashboard_avanzado')


# ─────────────────────────────────────────────────────────────
# REGISTRAR FATIGA (fetch desde JS)
# ─────────────────────────────────────────────────────────────
@csrf_exempt
def registrar_fatiga(request):
    if request.method != 'POST':
        return _json_error('Método no permitido', 405)

    usuario, err = _get_usuario_avanzado(request)
    if err:
        return _json_error('Sesión inválida', 401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return _json_error('JSON inválido', 400)

    ear       = float(data.get('ear', 0))
    parpadeos = int(data.get('parpadeos_por_minuto', 0))
    motivo    = data.get('motivo', 'EAR bajo + parpadeo excesivo')

    sesion = SesionAvanzada.objects.filter(usuario=usuario, activa=True).first()
    total_alertas_sesion = 0
    if sesion:
        total_alertas_sesion = HistorialAlerta.objects.filter(
            usuario=usuario, tipo='avanzado', creado_en__gte=sesion.inicio
        ).count()

    api_key = usuario.gemini_api_key or ''
    if api_key:
        prompt        = _build_prompt(usuario.nombre, ear, parpadeos, total_alertas_sesion + 1)
        recomendacion = _llamar_groq(api_key, prompt)
        if not recomendacion:
            recomendacion = 'No se pudo conectar con Groq. Verifica que tu API Key sea válida y tengas conexión a internet.'
    else:
        recomendacion = 'No hay API Key de Groq configurada. Ingresa tu clave en el banner amarillo.'

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

    if sesion:
        sesion.total_alertas = total_alertas_sesion + 1
        sesion.save(update_fields=['total_alertas'])

    return JsonResponse({
        'ok':            True,
        'alerta_id':     alerta.pk,
        'recomendacion': recomendacion,
        'ear':           ear,
        'parpadeos':     parpadeos,
        'hora':          alerta.creado_en.strftime('%H:%M'),
    })


# ─────────────────────────────────────────────────────────────
# HISTORIAL AVANZADO
# ─────────────────────────────────────────────────────────────
def historial_avanzado(request):
    import json
    usuario, err = _get_usuario_avanzado(request)
    if err:
        return err

    if request.method == 'POST' and request.POST.get('action') == 'limpiar':
        HistorialAlerta.objects.filter(usuario=usuario, tipo='avanzado').delete()
        return redirect('historial_avanzado')

    alertas           = HistorialAlerta.objects.filter(usuario=usuario, tipo='avanzado')
    total             = alertas.count()
    con_recomendacion = alertas.exclude(recomendacion_ia='').count()

    # ── Datos para gráfica 1: alertas por hora del día ──
    try:
        conteo_horas = {h: 0 for h in range(24)}
        for alerta in alertas:
            try:
                hora = alerta.creado_en.hour  # usar hora directa sin astimezone
            except Exception:
                hora = 0
            conteo_horas[hora] = conteo_horas.get(hora, 0) + 1

        horas_activas = [h for h in range(24) if conteo_horas[h] > 0 or (7 <= h <= 22)]
        horas_labels  = json.dumps([f"{h:02d}:00" for h in horas_activas])
        horas_data    = json.dumps([conteo_horas[h] for h in horas_activas])
    except Exception:
        horas_labels = json.dumps([f"{h:02d}:00" for h in range(7, 23)])
        horas_data   = json.dumps([0] * 16)

    # ── Datos para gráfica 2: evolución del EAR ──
    try:
        alertas_ear = list(alertas.exclude(ear_valor__isnull=True).order_by('creado_en'))
        ear_labels  = json.dumps([a.creado_en.strftime('%H:%M') for a in alertas_ear])
        ear_data    = json.dumps([round(float(a.ear_valor), 3) for a in alertas_ear])
    except Exception:
        ear_labels = json.dumps([])
        ear_data   = json.dumps([])

    return render(request, 'historial_avanzado.html', {
        'usuario':           usuario,
        'alertas':           alertas,
        'total':             total,
        'con_recomendacion': con_recomendacion,
        'horas_labels':      horas_labels,
        'horas_data':        horas_data,
        'ear_labels':        ear_labels,
        'ear_data':          ear_data,
    })


# ─────────────────────────────────────────────────────────────
# NOTIFICACIONES PENDIENTES (para notificador.py)
# Usa creado_en en lugar de campo notificado para evitar migraciones
# ─────────────────────────────────────────────────────────────
def notificaciones_pendientes(request):
    # Acepta usuario_id como parámetro GET para que el notificador.py
    # pueda consultarlo sin necesitar cookies de sesión
    usuario_id = request.GET.get('uid') or request.session.get('usuario_id')
    if not usuario_id:
        return JsonResponse({'notificaciones': []})
    try:
        usuario = Usuario.objects.get(pk=usuario_id)
    except Usuario.DoesNotExist:
        return JsonResponse({'notificaciones': []})

    # Alertas de los últimos 6 segundos
    desde   = timezone.now() - timezone.timedelta(seconds=6)
    alertas = HistorialAlerta.objects.filter(
        usuario=usuario,
        creado_en__gte=desde,
    ).order_by('-creado_en')[:5]

    notificaciones = []
    for alerta in alertas:
        if alerta.tipo == 'avanzado':
            titulo  = '👁️ EyeGuard — Fatiga visual detectada'
            mensaje = alerta.recomendacion_ia[:120] if alerta.recomendacion_ia else alerta.mensaje
        else:
            titulo  = f'⏱️ EyeGuard — {alerta.protocolo}'
            mensaje = alerta.mensaje
        notificaciones.append({'titulo': titulo, 'mensaje': mensaje})

    return JsonResponse({'notificaciones': notificaciones})
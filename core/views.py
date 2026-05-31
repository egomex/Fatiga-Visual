from django.shortcuts import render, redirect


def inicio(request):
    """
    Pantalla principal: ingreso de nombre y selección de modo.
    GET  → muestra el formulario.
    POST → guarda en sesión y redirige al dashboard correspondiente.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        mode     = request.POST.get('mode', 'basic')

        if not username:
            return render(request, 'index.html', {
                'error_nombre': True,
                'mode': mode,
            })

        request.session['username'] = username
        request.session['mode']     = mode

        if mode == 'advanced':
            return redirect('dashboard_avanzado')
        return redirect('dashboard_basico')

    return render(request, 'index.html')


def dashboard_basico(request):
    """
    Dashboard del modo básico.
    Muestra las 3 opciones: alertas predeterminadas, configurables e historial.
    Requiere que el usuario haya pasado por la pantalla de inicio.
    """
    username = request.session.get('username')
    if not username:
        return redirect('inicio')

    return render(request, 'dashboard_basico.html', {
        'username': username,
    })


# Placeholder para el modo avanzado (se implementará después)
def dashboard_avanzado(request):
    username = request.session.get('username')
    if not username:
        return redirect('inicio')

    return render(request, 'dashboard_avanzado.html', {
        'username': username,
    })
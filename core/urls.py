from django.urls import path
from . import views

urlpatterns = [
    # ── Autenticación ──
    path('',                                  views.inicio,                  name='inicio'),
    path('salir/',                            views.salir,                   name='salir'),
    path('cerrar-sesion/',                    views.cerrar_sesion,           name='cerrar_sesion'),

    # ── Modo básico ──
    path('dashboard/basico/',                 views.dashboard_basico,        name='dashboard_basico'),
    path('dashboard/basico/predeterminadas/', views.alertas_predeterminadas, name='alertas_predeterminadas'),
    path('dashboard/basico/configurables/',   views.alertas_configurables,   name='alertas_configurables'),
    path('dashboard/basico/historial/',       views.historial,               name='historial'),

    # ── Modo avanzado ──
    path('dashboard/avanzado/',               views.dashboard_avanzado,      name='dashboard_avanzado'),
    path('dashboard/avanzado/api-key/',       views.guardar_api_key,         name='guardar_api_key'),
    path('dashboard/avanzado/iniciar/',       views.iniciar_sesion_avanzada, name='iniciar_sesion_avanzada'),
    path('dashboard/avanzado/detener/',       views.detener_sesion_avanzada, name='detener_sesion_avanzada'),
    path('dashboard/avanzado/fatiga/',        views.registrar_fatiga,        name='registrar_fatiga'),
    path('dashboard/avanzado/historial/',     views.historial_avanzado,      name='historial_avanzado'),
    path('api/notificaciones-pendientes/', views.notificaciones_pendientes, name='notificaciones_pendientes'),
]
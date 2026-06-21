from django.urls import path
from . import views

urlpatterns = [
    path('',                                     views.inicio,                  name='inicio'),
    path('salir/',                               views.salir,                   name='salir'),
    path('cerrar-sesion/',                       views.cerrar_sesion,           name='cerrar_sesion'),
    path('dashboard/basico/',                    views.dashboard_basico,        name='dashboard_basico'),
    path('dashboard/basico/predeterminadas/',    views.alertas_predeterminadas, name='alertas_predeterminadas'),
    path('dashboard/basico/configurables/',      views.alertas_configurables,   name='alertas_configurables'),
    path('dashboard/basico/historial/',          views.historial,               name='historial'),
    # path('dashboard/avanzado/',               views.dashboard_avanzado,      name='dashboard_avanzado'),
]
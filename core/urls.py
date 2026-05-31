from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('dashboard/basico/', views.dashboard_basico, name='dashboard_basico'),

    # Se habilitará cuando se desarrolle el modo avanzado
    # path('dashboard/avanzado/', views.dashboard_avanzado, name='dashboard_avanzado'),
]
from django.db import models
from django.contrib.auth.hashers import make_password


class Usuario(models.Model):
    nombre    = models.CharField(max_length=40, unique=True)
    password  = models.CharField(max_length=255)          # almacenada con hash
    creado_en = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'


class HistorialAlerta(models.Model):
    TIPO_CHOICES = [
        ('preset', 'Predeterminada'),
        ('custom', 'Personalizada'),
    ]

    usuario    = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='historial')
    protocolo  = models.CharField(max_length=100)
    mensaje    = models.CharField(max_length=255)
    tipo       = models.CharField(max_length=10, choices=TIPO_CHOICES)
    completada = models.BooleanField(default=False)   # True cuando el usuario cierra el modal
    creado_en  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.usuario.nombre} — {self.protocolo} ({self.creado_en:%H:%M})'

    class Meta:
        ordering = ['-creado_en']
        verbose_name = 'Alerta'
        verbose_name_plural = 'Historial de alertas'


class ConfiguracionAlerta(models.Model):
    """Guarda la última configuración personalizada de cada usuario."""
    usuario          = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='configuracion')
    intervalo_trabajo = models.PositiveIntegerField(default=30)   # minutos
    duracion_descanso = models.PositiveIntegerField(default=5)    # minutos
    mensaje_custom    = models.CharField(max_length=120, blank=True, default='')
    sonido_activo     = models.BooleanField(default=True)
    actualizado_en    = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Config de {self.usuario.nombre}'

    class Meta:
        verbose_name = 'Configuración de alerta'
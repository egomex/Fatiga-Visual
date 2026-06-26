from django.db import models
from django.contrib.auth.hashers import make_password


class Usuario(models.Model):
    nombre         = models.CharField(max_length=40, unique=True)
    password       = models.CharField(max_length=255)
    gemini_api_key = models.CharField(max_length=200, blank=True, default='')
    creado_en      = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'


class HistorialAlerta(models.Model):
    TIPO_CHOICES = [
        ('preset',   'Predeterminada'),
        ('custom',   'Personalizada'),
        ('avanzado', 'Modo Avanzado'),
    ]

    usuario          = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='historial')
    protocolo        = models.CharField(max_length=100)
    mensaje          = models.CharField(max_length=255)
    tipo             = models.CharField(max_length=10, choices=TIPO_CHOICES)
    completada       = models.BooleanField(default=False)
    # Campos exclusivos del modo avanzado (null en alertas básicas)
    ear_valor        = models.FloatField(null=True, blank=True)
    parpadeos_minuto = models.IntegerField(null=True, blank=True)
    recomendacion_ia = models.TextField(blank=True, default='')
    creado_en        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.usuario.nombre} — {self.protocolo} ({self.creado_en:%H:%M})'

    class Meta:
        ordering = ['-creado_en']
        verbose_name = 'Alerta'
        verbose_name_plural = 'Historial de alertas'


class ConfiguracionAlerta(models.Model):
    """Última configuración personalizada del modo básico."""
    usuario           = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='configuracion')
    intervalo_trabajo = models.PositiveIntegerField(default=30)
    duracion_descanso = models.PositiveIntegerField(default=5)
    mensaje_custom    = models.CharField(max_length=120, blank=True, default='')
    sonido_activo     = models.BooleanField(default=True)
    actualizado_en    = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Config de {self.usuario.nombre}'

    class Meta:
        verbose_name = 'Configuración de alerta'


class SesionAvanzada(models.Model):
    """Registra cada sesión de monitoreo con cámara."""
    usuario           = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='sesiones_avanzadas')
    inicio            = models.DateTimeField(auto_now_add=True)
    fin               = models.DateTimeField(null=True, blank=True)
    activa            = models.BooleanField(default=True)
    total_alertas     = models.PositiveIntegerField(default=0)
    ear_promedio      = models.FloatField(null=True, blank=True)
    parpadeos_promedio = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f'Sesión {self.usuario.nombre} — {self.inicio:%d/%m/%Y %H:%M}'

    class Meta:
        ordering = ['-inicio']
        verbose_name = 'Sesión avanzada'
        verbose_name_plural = 'Sesiones avanzadas'
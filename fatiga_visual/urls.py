#from django.contrib import admin
#from django.urls import path, include

#urlpatterns = [
 #   path('admin/', admin.site.urls),
  #  path('', include('core.urls')),   # todas las rutas de la app core
#]
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('favicon.ico', RedirectView.as_view(url='/static/img/icon-192.png')),
] + static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

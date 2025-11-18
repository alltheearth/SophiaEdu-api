from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as authtoken_views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


router = DefaultRouter()

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('api/User/', include('apps.User.urls')),
                  path('api-auth/', include('rest_framework.urls')),
                  path('api-token-auth/', authtoken_views.obtain_auth_token, name='api-token-auth'),
                  # Arquivo do schema
                  path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

                  # Swagger UI
                  path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

                  # Redoc (opcional)
                  path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

] + router.urls

# ============================================
# ARQUIVOS ESTÁTICOS (DESENVOLVIMENTO)
# ============================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

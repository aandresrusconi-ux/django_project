from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EntidadViewSet, UsuarioViewSet

router = DefaultRouter()
router.register('entidades', EntidadViewSet, basename='entidad')
router.register('usuarios',  UsuarioViewSet, basename='usuario')

urlpatterns = [
    path('', include(router.urls)),
]

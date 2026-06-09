from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from apps.entidades.serializers import DashboardSerializer
from apps.entidades.models import SERVICIO_CHOICES

SRV_INFO = {
    'a': {'nombre': 'Servicio A', 'descripcion': 'Gestión y consulta de datos del servicio A.'},
    'b': {'nombre': 'Servicio B', 'descripcion': 'Acceso a reportes y estadísticas del servicio B.'},
    'c': {'nombre': 'Servicio C', 'descripcion': 'Administración de recursos del servicio C.'},
    'd': {'nombre': 'Servicio D', 'descripcion': 'Comunicaciones y notificaciones del servicio D.'},
    'e': {'nombre': 'Servicio E', 'descripcion': 'Archivo y documentación del servicio E.'},
}


class LoginView(APIView):
    """
    POST /api/auth/login/
    Body: { "username": "...", "password": "..." }
    Responde con access + refresh JWT.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip().lower()
        password = request.data.get('password', '')

        if not username or not password:
            return Response(
                {'error': 'Completá usuario y contraseña.'},
                status=400
            )

        user = authenticate(request, username=username, password=password)
        if not user:
            return Response(
                {'error': 'Usuario o contraseña incorrectos.'},
                status=401
            )
        if not user.is_active:
            return Response({'error': 'Usuario inactivo.'}, status=403)

        refresh = RefreshToken.for_user(user)
        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id':       user.id,
                'username': user.username,
                'nombre':   user.nombre,
                'email':    user.email,
                'is_staff': user.is_staff,
            }
        })


class RefreshView(APIView):
    """
    POST /api/auth/refresh/
    Body: { "refresh": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from rest_framework_simplejwt.exceptions import TokenError
        try:
            refresh = RefreshToken(request.data.get('refresh', ''))
            return Response({'access': str(refresh.access_token)})
        except TokenError:
            return Response({'error': 'Token inválido o expirado.'}, status=401)


class DashboardView(APIView):
    """
    GET /api/auth/dashboard/
    Devuelve datos del usuario autenticado + servicios activos/sin acceso con metadata.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = DashboardSerializer(user)
        data = serializer.data

        # Enriquecer servicios con info descriptiva
        data['servicios_activos_info'] = [
            {**SRV_INFO.get(s, {'nombre': f'Servicio {s.upper()}', 'descripcion': ''}), 'clave': s}
            for s in data['servicios_activos']
        ]
        data['servicios_sin_acceso_info'] = [
            {**SRV_INFO.get(s, {'nombre': f'Servicio {s.upper()}', 'descripcion': ''}), 'clave': s}
            for s in data['servicios_sin_acceso']
        ]
        return Response(data)

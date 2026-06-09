from rest_framework import serializers
from .models import Entidad, Usuario, TODOS_SERVICIOS


# ── Entidad ───────────────────────────────────────────────────────────────────

class EntidadSerializer(serializers.ModelSerializer):
    total_usuarios = serializers.SerializerMethodField()

    class Meta:
        model  = Entidad
        fields = ['id', 'nombre', 'servicios', 'srv_usuarios', 'creado_en', 'total_usuarios']
        read_only_fields = ['id', 'creado_en', 'total_usuarios']

    def get_total_usuarios(self, obj):
        return obj.usuarios.count()

    def validate_servicios(self, value):
        invalidos = [s for s in value if s not in TODOS_SERVICIOS]
        if invalidos:
            raise serializers.ValidationError(
                f"Servicios inválidos: {invalidos}. Válidos: {TODOS_SERVICIOS}"
            )
        return list(set(value))  # deduplicar

    def validate_srv_usuarios(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("srv_usuarios debe ser un objeto JSON.")
        return value


# ── Usuario ───────────────────────────────────────────────────────────────────

class UsuarioSerializer(serializers.ModelSerializer):
    entidad_nombre   = serializers.CharField(source='entidad.nombre', read_only=True)
    servicios_activos = serializers.ListField(read_only=True)

    class Meta:
        model  = Usuario
        fields = [
            'id', 'entidad', 'entidad_nombre',
            'nombre', 'username', 'email',
            'servicios', 'servicios_activos',
            'is_active', 'creado_en',
        ]
        read_only_fields = ['id', 'creado_en', 'entidad_nombre', 'servicios_activos']

    def validate_servicios(self, value):
        invalidos = [s for s in value if s not in TODOS_SERVICIOS]
        if invalidos:
            raise serializers.ValidationError(f"Servicios inválidos: {invalidos}")
        return value

    def validate(self, attrs):
        entidad = attrs.get('entidad') or (self.instance.entidad if self.instance else None)
        servicios = attrs.get('servicios', self.instance.servicios if self.instance else [])
        if entidad:
            no_habilitados = [s for s in servicios if s not in entidad.servicios]
            if no_habilitados:
                raise serializers.ValidationError({
                    'servicios': f"Servicios no habilitados por la entidad: {no_habilitados}"
                })
        return attrs


class UsuarioCreateSerializer(UsuarioSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta(UsuarioSerializer.Meta):
        fields = UsuarioSerializer.Meta.fields + ['password']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UsuarioUpdateSerializer(UsuarioSerializer):
    password = serializers.CharField(write_only=True, min_length=6, required=False, allow_blank=True)

    class Meta(UsuarioSerializer.Meta):
        fields = UsuarioSerializer.Meta.fields + ['password']

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


# ── Dashboard (portal) ────────────────────────────────────────────────────────

class DashboardSerializer(serializers.ModelSerializer):
    entidad_nombre      = serializers.CharField(source='entidad.nombre', read_only=True)
    entidad_servicios   = serializers.ListField(source='entidad.servicios', read_only=True)
    srv_usuarios        = serializers.DictField(source='entidad.srv_usuarios', read_only=True)
    servicios_activos   = serializers.ListField(read_only=True)
    servicios_sin_acceso = serializers.ListField(read_only=True)

    class Meta:
        model  = Usuario
        fields = [
            'id', 'nombre', 'username', 'email', 'creado_en',
            'entidad', 'entidad_nombre', 'entidad_servicios', 'srv_usuarios',
            'servicios', 'servicios_activos', 'servicios_sin_acceso',
        ]
        read_only_fields = fields

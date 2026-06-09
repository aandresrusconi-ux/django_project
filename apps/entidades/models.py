from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator


SERVICIO_CHOICES = [
    ('a', 'Servicio A'),
    ('b', 'Servicio B'),
    ('c', 'Servicio C'),
    ('d', 'Servicio D'),
    ('e', 'Servicio E'),
]
TODOS_SERVICIOS = [s[0] for s in SERVICIO_CHOICES]


class Entidad(models.Model):
    """
    Organismo/entidad.
    - servicios: lista de servicios habilitados para esta entidad (ManyToMany implícito via JSON)
    - srv_usuarios: dict {"a": "enar_Dd", "b": "otro"} — identificador de usuario por servicio
    """
    nombre       = models.CharField(max_length=255, unique=True)
    servicios    = models.JSONField(default=list, blank=True,
                                    help_text='Lista de claves de servicio habilitados, ej: ["a","c"]')
    srv_usuarios = models.JSONField(default=dict, blank=True,
                                    help_text='Dict servicio→identificador, ej: {"a":"enar_Dd"}')
    creado_en    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Entidad'
        verbose_name_plural = 'Entidades'
        ordering            = ['nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        # Asegurar que servicios solo contenga claves válidas
        self.servicios = [s for s in (self.servicios or []) if s in TODOS_SERVICIOS]
        # Limpiar srv_usuarios: solo para servicios activos
        self.srv_usuarios = {
            k: v for k, v in (self.srv_usuarios or {}).items()
            if k in self.servicios and v
        }
        super().save(*args, **kwargs)
        # Cascada: quitar servicios que ya no están en la entidad a sus usuarios
        self.usuarios.all().update_services_cascade(self.servicios)

    def get_servicios_display(self):
        return [dict(SERVICIO_CHOICES).get(s, s) for s in self.servicios]


class UsuarioManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra):
        if not username:
            raise ValueError('El nombre de usuario es obligatorio.')
        if not email:
            raise ValueError('El email es obligatorio.')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra)

    def update_services_cascade(self, entidad_servicios):
        """Quita a todos los usuarios de esta queryset los servicios no habilitados."""
        for u in self.all():
            nuevos = [s for s in u.servicios if s in entidad_servicios]
            if nuevos != u.servicios:
                u.servicios = nuevos
                u.save(update_fields=['servicios'])


username_validator = RegexValidator(
    r'^[a-z0-9._-]{3,50}$',
    'Solo letras minúsculas, números, punto y guión. Entre 3 y 50 caracteres.'
)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    Usuario del sistema. El login es por `username`.
    Cada usuario pertenece a una entidad y tiene sus propios servicios asignados
    (subconjunto de los que la entidad habilita).
    """
    entidad   = models.ForeignKey(
        Entidad, on_delete=models.CASCADE,
        related_name='usuarios', null=True, blank=True
    )
    nombre    = models.CharField(max_length=255)
    username  = models.CharField(
        max_length=100, unique=True,
        validators=[username_validator]
    )
    email     = models.EmailField(unique=True)
    servicios = models.JSONField(default=list, blank=True,
                                  help_text='Servicios asignados a este usuario (subconjunto de los de la entidad)')
    is_active = models.BooleanField(default=True)
    is_staff  = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    objects = UsuarioManager()

    USERNAME_FIELD  = 'username'
    REQUIRED_FIELDS = ['email', 'nombre']

    class Meta:
        verbose_name        = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering            = ['nombre']

    def __str__(self):
        return f'{self.nombre} (@{self.username})'

    def save(self, *args, **kwargs):
        self.username = self.username.lower().strip()
        # Filtrar servicios contra los de la entidad
        if self.entidad:
            self.servicios = [s for s in (self.servicios or []) if s in self.entidad.servicios]
        super().save(*args, **kwargs)

    @property
    def servicios_activos(self):
        """Servicios efectivos: intersección entre los de la entidad y los del usuario."""
        if not self.entidad:
            return []
        return [s for s in self.entidad.servicios if s in self.servicios]

    @property
    def servicios_sin_acceso(self):
        """Servicios habilitados en la entidad pero no asignados al usuario."""
        if not self.entidad:
            return []
        return [s for s in self.entidad.servicios if s not in self.servicios]

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from import_export.admin import ImportExportModelAdmin
from .models import Entidad, Usuario
from .resources import EntidadResource


@admin.register(Entidad)
class EntidadAdmin(ImportExportModelAdmin):
    resource_class  = EntidadResource
    list_display    = ['nombre', 'get_servicios', 'total_usuarios', 'creado_en']
    search_fields   = ['nombre']
    list_filter     = ['creado_en']
    readonly_fields = ['creado_en']

    def get_servicios(self, obj):
        return ' | '.join(obj.servicios).upper() if obj.servicios else '—'
    get_servicios.short_description = 'Servicios'

    def total_usuarios(self, obj):
        return obj.usuarios.count()
    total_usuarios.short_description = 'Usuarios'


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display   = ['username', 'nombre', 'email', 'entidad', 'get_servicios', 'is_active', 'creado_en']
    search_fields  = ['username', 'nombre', 'email']
    list_filter    = ['entidad', 'is_active', 'is_staff']
    ordering       = ['nombre']
    fieldsets = (
        (None,            {'fields': ('username', 'password')}),
        ('Datos',         {'fields': ('nombre', 'email', 'entidad', 'servicios')}),
        ('Permisos',      {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields':  ('username', 'email', 'nombre', 'entidad', 'servicios', 'password1', 'password2'),
        }),
    )

    def get_servicios(self, obj):
        return ' | '.join(obj.servicios).upper() if obj.servicios else '—'
    get_servicios.short_description = 'Servicios'

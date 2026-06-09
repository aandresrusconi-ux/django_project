"""
Recursos para django-import-export.
Permite importar entidades desde CSV o XLSX con mapeo de columnas.
Columna obligatoria: organismo → nombre
Columnas opcionales: servicios, srv_usuario (identificador)
"""
import json
from import_export import resources, fields
from import_export.widgets import Widget
from .models import Entidad, TODOS_SERVICIOS


class ServiciosWidget(Widget):
    """Parsea una celda de texto con servicios como 'a,b,c' o 'A B C' → lista."""
    def clean(self, value, row=None, **kwargs):
        if not value:
            return []
        raw = str(value).lower()
        return [s for s in TODOS_SERVICIOS if s in raw]

    def render(self, value, obj=None):
        return ', '.join(value).upper() if value else ''


class EntidadResource(resources.ModelResource):
    # Campo fuente en el archivo de importación → campo del modelo
    organismo   = fields.Field(attribute='nombre',       column_name='organismo')
    servicios   = fields.Field(attribute='servicios',    column_name='servicios',    widget=ServiciosWidget())
    srv_usuario = fields.Field(attribute='_srv_usuario', column_name='srv_usuario')

    class Meta:
        model          = Entidad
        import_id_fields = ['nombre']          # identifica duplicados por nombre
        fields         = ('organismo', 'servicios', 'srv_usuario')
        skip_unchanged = False
        # Al encontrar duplicado → raise error (se maneja en la vista)

    def before_import_row(self, row, row_number=None, **kwargs):
        """Normalizar nombre a mayúsculas antes de importar."""
        if 'organismo' in row and row['organismo']:
            row['organismo'] = str(row['organismo']).upper().strip()

    def after_import_row(self, row, row_result, row_number=None, **kwargs):
        """Guardar el identificador de usuario por servicio después de importar la fila."""
        if row_result.errors:
            return
        srv_usuario_val = str(row.get('srv_usuario') or '').strip()
        if srv_usuario_val and row_result.object_id:
            try:
                entidad = Entidad.objects.get(pk=row_result.object_id)
                if entidad.servicios:
                    entidad.srv_usuarios = {s: srv_usuario_val for s in entidad.servicios}
                    entidad.save(update_fields=['srv_usuarios'])
            except Entidad.DoesNotExist:
                pass

    def get_or_init_instance(self, instance_loader, row):
        """Si ya existe, levantamos error en lugar de actualizar."""
        instance, new = super().get_or_init_instance(instance_loader, row)
        if not new:
            from import_export.results import Error
            raise Exception(
                f"La entidad «{row.get('organismo', '')}» ya existe. "
                "La importación fue detenida y revertida."
            )
        return instance, new

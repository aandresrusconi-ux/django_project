import csv
import io
from django.http import HttpResponse
from django.db import transaction
from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from import_export.formats.base_formats import CSV, XLSX

from .models import Entidad, Usuario
from .serializers import (
    EntidadSerializer,
    UsuarioSerializer,
    UsuarioCreateSerializer,
    UsuarioUpdateSerializer,
)
from .permissions import IsAdminUser
from .resources import EntidadResource


# ── Entidades ─────────────────────────────────────────────────────────────────

class EntidadViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de entidades.
    GET    /api/entidades/          → lista
    POST   /api/entidades/          → crear
    GET    /api/entidades/{id}/     → detalle
    PUT    /api/entidades/{id}/     → actualizar completo
    PATCH  /api/entidades/{id}/     → actualizar parcial
    DELETE /api/entidades/{id}/     → eliminar
    GET    /api/entidades/{id}/usuarios/  → usuarios de la entidad
    GET    /api/entidades/exportar_csv/   → CSV
    GET    /api/entidades/exportar_xlsx/  → XLSX
    POST   /api/entidades/importar/       → importar CSV/XLSX
    POST   /api/entidades/previsualizar/  → previsualizar columnas antes de importar
    """
    queryset           = Entidad.objects.all()
    serializer_class   = EntidadSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=['get'], url_path='usuarios')
    def usuarios(self, request, pk=None):
        entidad = self.get_object()
        qs = entidad.usuarios.all()
        serializer = UsuarioSerializer(qs, many=True)
        return Response(serializer.data)

    # ── Exportar CSV ──────────────────────────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='exportar_csv')
    def exportar_csv(self, request):
        resource = EntidadResource()
        dataset  = resource.export(queryset=Entidad.objects.all())
        response = HttpResponse(dataset.csv, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="entidades.csv"'
        # Agregar BOM UTF-8 para Excel
        response.content = b'\xef\xbb\xbf' + response.content
        return response

    # ── Exportar XLSX ─────────────────────────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='exportar_xlsx')
    def exportar_xlsx(self, request):
        resource = EntidadResource()
        dataset  = resource.export(queryset=Entidad.objects.all())
        response = HttpResponse(
            dataset.xlsx,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="entidades.xlsx"'
        return response

    # ── Exportar Usuarios CSV ─────────────────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='exportar_usuarios_csv')
    def exportar_usuarios_csv(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="usuarios.csv"'
        response.write('\xef\xbb\xbf')
        writer = csv.writer(response)
        writer.writerow(['ID', 'Nombre', 'Usuario', 'Email', 'Entidad', 'Servicios', 'Fecha de alta'])
        for u in Usuario.objects.select_related('entidad').all():
            writer.writerow([
                u.id, u.nombre, u.username, u.email,
                u.entidad.nombre if u.entidad else '',
                ' | '.join(u.servicios).upper(),
                u.creado_en.strftime('%d/%m/%Y %H:%M'),
            ])
        return response

    # ── Previsualizar columnas ────────────────────────────────────────────────
    @action(
        detail=False, methods=['post'], url_path='previsualizar',
        parser_classes=[parsers.MultiPartParser]
    )
    def previsualizar(self, request):
        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response({'error': 'No se recibió ningún archivo.'}, status=400)

        ext = archivo.name.rsplit('.', 1)[-1].lower()
        try:
            if ext == 'csv':
                headers, rows = _parse_csv_preview(archivo)
            elif ext == 'xlsx':
                headers, rows = _parse_xlsx_preview(archivo)
            else:
                return Response({'error': 'Formato no soportado. Usá .csv o .xlsx'}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

        return Response({
            'headers':    headers,
            'preview':    rows[:5],
            'total_rows': len(rows),
        })

    # ── Importar ──────────────────────────────────────────────────────────────
    @action(
        detail=False, methods=['post'], url_path='importar',
        parser_classes=[parsers.MultiPartParser]
    )
    def importar(self, request):
        archivo        = request.FILES.get('archivo')
        col_organismo  = request.data.get('col_organismo')
        col_servicios  = request.data.get('col_servicios')
        col_srv_usuario = request.data.get('col_srv_usuario')

        if not archivo:
            return Response({'error': 'No se recibió ningún archivo.'}, status=400)
        if col_organismo is None:
            return Response({'error': 'Debés indicar la columna de organismo.'}, status=400)

        col_org  = int(col_organismo)
        col_srv  = int(col_servicios)  if col_servicios  not in (None, '', '-1') else -1
        col_uid  = int(col_srv_usuario) if col_srv_usuario not in (None, '', '-1') else -1

        ext = archivo.name.rsplit('.', 1)[-1].lower()
        try:
            if ext == 'csv':
                _, rows = _parse_csv_preview(archivo)
            elif ext == 'xlsx':
                _, rows = _parse_xlsx_preview(archivo)
            else:
                return Response({'error': 'Formato no soportado.'}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

        resultados = []
        try:
            with transaction.atomic():
                for row in rows:
                    nombre = row[col_org].upper().strip() if col_org < len(row) else ''
                    if not nombre:
                        resultados.append({'nombre': '(vacío)', 'status': 'skip', 'msg': 'Fila vacía'})
                        continue

                    if Entidad.objects.filter(nombre=nombre).exists():
                        raise ValueError(
                            f"La entidad «{nombre}» ya existe. Importación detenida y revertida."
                        )

                    servicios = []
                    if col_srv >= 0 and col_srv < len(row):
                        raw = row[col_srv].lower()
                        servicios = [s for s in ['a','b','c','d','e'] if s in raw]

                    srv_usuario = ''
                    if col_uid >= 0 and col_uid < len(row):
                        srv_usuario = row[col_uid].strip()

                    srv_usuarios = {s: srv_usuario for s in servicios} if srv_usuario else {}

                    Entidad.objects.create(
                        nombre=nombre,
                        servicios=servicios,
                        srv_usuarios=srv_usuarios,
                    )
                    resultados.append({'nombre': nombre, 'status': 'ok', 'msg': 'Importado'})

        except ValueError as e:
            resultados.append({'nombre': '', 'status': 'error', 'msg': str(e)})
            return Response({
                'ok':    False,
                'msg':   str(e),
                'items': resultados,
            }, status=400)

        ok_count = sum(1 for r in resultados if r['status'] == 'ok')
        return Response({
            'ok':    True,
            'msg':   f'{ok_count} entidades importadas.',
            'items': resultados,
        })


# ── Usuarios ──────────────────────────────────────────────────────────────────

class UsuarioViewSet(viewsets.ModelViewSet):
    """
    CRUD de usuarios (admin).
    GET    /api/usuarios/
    POST   /api/usuarios/
    GET    /api/usuarios/{id}/
    PUT/PATCH /api/usuarios/{id}/
    DELETE /api/usuarios/{id}/
    """
    queryset           = Usuario.objects.select_related('entidad').all()
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'create':
            return UsuarioCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UsuarioUpdateSerializer
        return UsuarioSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        entidad_id = self.request.query_params.get('entidad_id')
        if entidad_id:
            qs = qs.filter(entidad_id=entidad_id)
        return qs


# ── Helpers de parseo ─────────────────────────────────────────────────────────

def _parse_csv_preview(archivo, max_rows=200):
    raw = archivo.read()
    if not raw.startswith(b'\xef\xbb\xbf'):
        try:
            raw = raw.decode('utf-8')
        except UnicodeDecodeError:
            raw = raw.decode('windows-1252', errors='replace')
    else:
        raw = raw[3:].decode('utf-8')

    # Detectar delimitador
    sample = raw[:2000]
    delimiters = {';': sample.count(';'), ',': sample.count(','),
                  '\t': sample.count('\t'), '|': sample.count('|')}
    delim = max(delimiters, key=delimiters.get)

    reader = csv.reader(io.StringIO(raw), delimiter=delim)
    headers = []
    rows = []
    for i, row in enumerate(reader):
        row = [c.strip() for c in row]
        if i == 0:
            headers = row
        elif len(rows) < max_rows:
            rows.append(row)
    return headers, rows


def _parse_xlsx_preview(archivo, max_rows=200):
    import openpyxl
    wb = openpyxl.load_workbook(filename=io.BytesIO(archivo.read()), read_only=True, data_only=True)
    ws = wb.active
    headers = []
    rows = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        row = [str(c).strip() if c is not None else '' for c in row]
        if i == 0:
            headers = row
        elif len(rows) < max_rows:
            rows.append(row)
    wb.close()
    return headers, rows

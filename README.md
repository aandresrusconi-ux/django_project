# Gestión de Entidades y Portal de Servicios — Django + DRF

## Stack
- Python 3.11+ / Django 4.2
- Django REST Framework + SimpleJWT
- PostgreSQL
- django-import-export (CSV / XLSX)
- openpyxl

---

## Estructura del proyecto

```
django_project/
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── entidades/          ← modelos, serializers, vistas admin, importador
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── permissions.py
│   │   ├── resources.py    ← django-import-export
│   │   ├── admin.py
│   │   └── management/commands/crear_admin.py
│   └── portal/             ← login JWT + dashboard del usuario
│       ├── views.py
│       └── urls.py
├── manage.py
├── requirements.txt
└── .env.example
```

---

## Instalación rápida

```bash
# 1. Clonar / descomprimir el proyecto
cd django_project

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de PostgreSQL

# 5. Crear la base de datos en PostgreSQL
psql -U postgres -c "CREATE DATABASE entidades_db;"

# 6. Migraciones
python manage.py makemigrations
python manage.py migrate

# 7. Crear superusuario admin
python manage.py crear_admin --username admin --password admin123

# 8. Correr el servidor
python manage.py runserver
```

---

## Endpoints de la API

### Autenticación (portal de usuario)

| Método | Endpoint              | Descripción                        |
|--------|-----------------------|------------------------------------|
| POST   | `/api/auth/login/`    | Login por username+password → JWT  |
| POST   | `/api/auth/refresh/`  | Refrescar access token             |
| GET    | `/api/auth/dashboard/`| Dashboard del usuario autenticado  |

**Login request:**
```json
{ "username": "ana.garcia", "password": "mipass" }
```

**Login response:**
```json
{
  "access":  "<JWT access token>",
  "refresh": "<JWT refresh token>",
  "user": { "id": 1, "username": "ana.garcia", "nombre": "Ana García", "is_staff": false }
}
```

---

### Administración (requiere is_staff=True)

Todos los endpoints requieren header:
```
Authorization: Bearer <access token>
```

#### Entidades

| Método | Endpoint                                  | Descripción                    |
|--------|-------------------------------------------|--------------------------------|
| GET    | `/api/entidades/`                         | Listar entidades               |
| POST   | `/api/entidades/`                         | Crear entidad                  |
| GET    | `/api/entidades/{id}/`                    | Detalle                        |
| PUT    | `/api/entidades/{id}/`                    | Actualizar completo            |
| PATCH  | `/api/entidades/{id}/`                    | Actualizar parcial             |
| DELETE | `/api/entidades/{id}/`                    | Eliminar (cascada a usuarios)  |
| GET    | `/api/entidades/{id}/usuarios/`           | Usuarios de la entidad         |
| GET    | `/api/entidades/exportar_csv/`            | Descargar CSV de entidades     |
| GET    | `/api/entidades/exportar_xlsx/`           | Descargar XLSX de entidades    |
| GET    | `/api/entidades/exportar_usuarios_csv/`   | Descargar CSV de usuarios      |
| POST   | `/api/entidades/previsualizar/`           | Previsualizar columnas archivo |
| POST   | `/api/entidades/importar/`                | Importar desde CSV/XLSX        |

**Crear entidad:**
```json
{
  "nombre": "MUNICIPIO DE LA PLATA",
  "servicios": ["a", "b", "e"],
  "srv_usuarios": { "a": "enar_Dd", "b": "otro_usr" }
}
```

**Previsualizar archivo (multipart):**
```
POST /api/entidades/previsualizar/
archivo: <file.csv o file.xlsx>
```
Responde:
```json
{
  "headers": ["organismo", "servicios", "referente", "provincia"],
  "preview": [["MUNICIPIO LA PLATA", "a,b", "enar_Dd", "PBA"]],
  "total_rows": 42
}
```

**Importar (multipart):**
```
POST /api/entidades/importar/
archivo:         <file>
col_organismo:   0      ← índice de la columna (desde previsualizar)
col_servicios:   1      ← opcional, -1 para ignorar
col_srv_usuario: 2      ← opcional, -1 para ignorar
```

#### Usuarios

| Método | Endpoint             | Descripción                   |
|--------|----------------------|-------------------------------|
| GET    | `/api/usuarios/`     | Listar (filtro: ?entidad_id=) |
| POST   | `/api/usuarios/`     | Crear usuario                 |
| GET    | `/api/usuarios/{id}/`| Detalle                       |
| PUT    | `/api/usuarios/{id}/`| Actualizar (password opcional)|
| DELETE | `/api/usuarios/{id}/`| Eliminar                      |

**Crear usuario:**
```json
{
  "entidad": 1,
  "nombre":   "Ana García",
  "username": "ana.garcia",
  "email":    "ana@ejemplo.com",
  "password": "mipass123",
  "servicios": ["a", "b"]
}
```

---

## Reglas de negocio implementadas

- El nombre de entidad se guarda **en mayúsculas** automáticamente.
- Los servicios de usuario se **filtran contra los de la entidad** al guardar.
- Si la entidad **quita un servicio**, se propaga a todos sus usuarios.
- Al importar, si un organismo **ya existe** → la importación se **detiene y revierte** por completo (transacción atómica).
- El login es por `username` (no email).
- Contraseñas hasheadas con bcrypt (Django `set_password`).

---

## Variables de entorno (.env)

| Variable              | Default               | Descripción                      |
|-----------------------|-----------------------|----------------------------------|
| SECRET_KEY            | (requerida)           | Clave secreta Django             |
| DEBUG                 | True                  | Modo debug                       |
| ALLOWED_HOSTS         | *                     | Hosts permitidos                 |
| DB_NAME               | entidades_db          | Nombre de la base de datos       |
| DB_USER               | postgres              | Usuario PostgreSQL                |
| DB_PASSWORD           | (requerida)           | Contraseña PostgreSQL             |
| DB_HOST               | localhost             | Host de la BD                    |
| DB_PORT               | 5432                  | Puerto de la BD                  |
| CORS_ALLOWED_ORIGINS  | http://localhost:3000 | Orígenes permitidos para CORS    |

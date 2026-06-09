"""
Comando para crear el superusuario admin inicial.
Uso: python manage.py crear_admin
"""
from django.core.management.base import BaseCommand
from apps.entidades.models import Usuario


class Command(BaseCommand):
    help = 'Crea el usuario administrador inicial'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin')
        parser.add_argument('--email',    default='admin@example.com')
        parser.add_argument('--password', default='admin123')
        parser.add_argument('--nombre',   default='Administrador')

    def handle(self, *args, **options):
        u = options['username']
        if Usuario.objects.filter(username=u).exists():
            self.stdout.write(self.style.WARNING(f'El usuario «{u}» ya existe.'))
            return
        Usuario.objects.create_superuser(
            username=u,
            email=options['email'],
            password=options['password'],
            nombre=options['nombre'],
        )
        self.stdout.write(self.style.SUCCESS(f'Superusuario «{u}» creado exitosamente.'))

from django.db import models
from django.contrib.auth.models import User


class UsuarioRegistro(models.Model):
    TIPOS_USUARIO = [
        ('B2C', 'Cliente'),
        ('B2B', 'Empresa'),
    ]
    nombre = models.CharField(max_length=60)
    rut = models.CharField(max_length=15, unique=True)
    correo = models.EmailField(max_length=60)
    clave = models.CharField(max_length=50)
    tipo_usuario = models.CharField(max_length=3, choices=TIPOS_USUARIO)

    # Campos solo para empresa
    razon_social = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.nombre


class Trabajador(models.Model):
    id_trabajador = models.AutoField(primary_key=True)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    cargo = models.CharField(max_length=20, choices=[('Bodeguero', 'Bodeguero'), ('Administrador', 'Administrador')], default='Bodeguero')
    fecha_ingreso = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.cargo}"


class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    stock = models.PositiveIntegerField(default=0)
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.nombre


class Pedido(models.Model):
    usuario = models.ForeignKey(UsuarioRegistro, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=[
        ('Pendiente', 'Pendiente'),
        ('En preparación', 'En preparación'),
        ('Despachado', 'Despachado'),
        ('Entregado', 'Entregado')
    ])
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.nombre}"

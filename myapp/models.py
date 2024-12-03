from django.contrib.auth.models import AbstractUser
from django.db import models, IntegrityError
from django.utils import timezone
from django.core.files.base import ContentFile
import barcode
from barcode.writer import ImageWriter
from io import BytesIO

class CustomUser(AbstractUser):
    cargo = models.CharField(max_length=150)
    horas = models.IntegerField(default=0)
    cbarra = models.IntegerField(null=True, blank=True, unique=True)  # Código único
    barcode_image = models.ImageField(upload_to='barcodes/', blank=True, null=True)
    salario_por_hora = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)  # Campo de salario

    def save(self, *args, **kwargs):
        if not self.cbarra:
            # Generar un código único si no se proporciona
            self.cbarra = CustomUser.objects.count() + 1
        
        # Generar la imagen del código de barras
        code = barcode.get('code128', str(self.cbarra), writer=ImageWriter())
        buffer = BytesIO()
        code.write(buffer)
        image_path = f'{self.cbarra}.png'
        print(f"Guardando imagen de código de barras en: {image_path}")  # Debug
        self.barcode_image.save(image_path, ContentFile(buffer.getvalue()), save=False)
        
        # Verificar unicidad del código de barras
        if CustomUser.objects.filter(cbarra=self.cbarra).exclude(id=self.id).exists():
            raise IntegrityError('El código de barras ya está en uso. Por favor, elige otro.')

        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class WorkSession(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

    def duration(self):
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 3600  # Convertir a horas
        return 0


class RegistroAsistencia(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    entrada = models.DateTimeField(auto_now_add=True)
    salida = models.DateTimeField(null=True, blank=True)
    completo = models.BooleanField(default=False)  # Indicador de horas completas

    def registrar_salida(self):
        self.salida = timezone.now()
        self.save()
        self.actualizar_completo()

    def actualizar_completo(self):
        if self.salida and self.entrada:
            horas_trabajadas = (self.salida - self.entrada).total_seconds() / 3600  # Calcular horas
            self.completo = horas_trabajadas >= self.user.horas  # Verificar si cumple horas
            self.save()




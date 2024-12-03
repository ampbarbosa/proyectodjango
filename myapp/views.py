from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib.auth.hashers import check_password
from django.http import HttpResponse
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q
from .forms import RegisterForm, LoginForm, WorkSessionForm
from .models import CustomUser, WorkSession, RegistroAsistencia  # Asegúrate de que estos modelos existan en models.py
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from django.core.files.base import ContentFile
from datetime import datetime
import csv
import io
from django.template.loader import get_template
from xhtml2pdf import pisa
from datetime import datetime

def edit_employees_view(request):
    # Tu lógica para la vista de edición de empleados
    employees = CustomUser.objects.all()  # Cambiado de Employee a CustomUser
    context = {'employees': employees}
    return render(request, 'edit_employees.html', context)

def delete_employee(request, employee_id):
    employee = get_object_or_404(CustomUser, id=employee_id)  # Cambiado de Employee a CustomUser
    employee.delete()
    messages.success(request, 'Empleado eliminado exitosamente.')
    return redirect('edit_employees')

def calcular_horas_trabajadas(entrada, salida):
    if entrada and salida:
        return (salida - entrada).total_seconds() / 3600  # Convierte segundos a horas
    return 0

def calcular_diferencia_horas(asignadas, trabajadas):
    return trabajadas - asignadas

def calcular_salario_generado(horas_trabajadas, salario_por_hora):
    return horas_trabajadas * float(salario_por_hora)


@login_required
def home_view(request):
    if request.method == "POST":
        cbarra = request.POST.get("cbarra")
        
        if not cbarra:
            messages.error(request, "Por favor, escanea tu código de barras.")
            return redirect('home')

        try:
            cbarra = int(cbarra)
        except ValueError:
            messages.error(request, "Código de barras inválido.")
            return redirect('home')

        user = get_object_or_404(CustomUser, cbarra=cbarra)

        # Obtener la fecha y hora actuales con la zona horaria correcta
        ahora = timezone.now()

        # Verificar si hay un registro de asistencia para hoy sin salida
        asistencia = RegistroAsistencia.objects.filter(user=user, entrada__date=ahora.date()).order_by('-entrada').first()

        if asistencia and asistencia.salida is None:
            asistencia.registrar_salida()
            messages.success(request, f"Salida registrada para {user.email}.")
        else:
            RegistroAsistencia.objects.create(user=user, entrada=ahora)
            messages.success(request, f"Entrada registrada para {user.email}.")

        return redirect('home')

    return render(request, 'home.html')

@login_required
def asistencia_view(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    if fecha_inicio and fecha_fin:
        registros = RegistroAsistencia.objects.filter(
            entrada__date__range=[fecha_inicio, fecha_fin]
        ).order_by('-entrada')
        # Guardar las fechas en la sesión
        request.session['fecha_inicio'] = fecha_inicio
        request.session['fecha_fin'] = fecha_fin
    elif fecha_inicio:
        registros = RegistroAsistencia.objects.filter(
            entrada__date=fecha_inicio
        ).order_by('-entrada')
        # Guardar la fecha de inicio en la sesión
        request.session['fecha_inicio'] = fecha_inicio
        request.session['fecha_fin'] = None
    else:
        registros = RegistroAsistencia.objects.all().order_by('-entrada')
        # Limpiar las fechas en la sesión
        request.session['fecha_inicio'] = None
        request.session['fecha_fin'] = None

    for registro in registros:
        registro.horas_trabajadas = calcular_horas_trabajadas(registro.entrada, registro.salida)
        registro.diferencia_horas = calcular_diferencia_horas(registro.user.horas, registro.horas_trabajadas)
        registro.salario_generado = calcular_salario_generado(registro.horas_trabajadas, registro.user.salario_por_hora)
        
        # Impresiones de depuración
        print(f"Usuario: {registro.user.email}")
        print(f"Horas Trabajadas: {registro.horas_trabajadas}")
        print(f"Salario por Hora: {registro.user.salario_por_hora}")
        print(f"Salario Generado: {registro.salario_generado}")
    
    return render(request, 'asistencia.html', {'registros': registros})

@login_required
def end_work_session(request, session_id):
    work_session = WorkSession.objects.get(id=session_id)
    work_session.end_time = timezone.now()
    work_session.save()
    # Actualizar las horas trabajadas en el perfil del usuario
    user = request.user
    user.horas += work_session.duration()
    user.save()
    return redirect('home')

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cuenta creada exitosamente. Por favor, inicia sesión.')
            return redirect('login')
        else:
            messages.error(request, 'No se pudo crear el usuario. Verifica los datos ingresados.')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = CustomUser.objects.filter(email=email).first()
            if user and check_password(password, user.password):
                login(request, user)
                return redirect('home')
            else:
                form.add_error(None, 'Las credenciales no son correctas.')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

@login_required
def welcome_view(request):
    return render(request, 'welcome.html')

def admin_login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = CustomUser.objects.filter(email=email, cargo='admin').first()
            if user and check_password(password, user.password):
                login(request, user)
                return redirect('edit_employees')
            else:
                form.add_error(None, 'Las credenciales no son correctas o no tienes permisos de administrador.')
    else:
        form = LoginForm()
    return render(request, 'admin_login.html', {'form': form})

@login_required
def edit_employees_view(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user = CustomUser.objects.get(id=user_id)
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.cargo = request.POST.get('cargo')
        user.horas = request.POST.get('horas')
        user.cbarra = request.POST.get('cbarra')
        
        salario_por_hora = request.POST.get('salario_por_hora')  # Obtener salario_por_hora
        if salario_por_hora:  # Validar si el salario_por_hora no está vacío
            try:
                user.salario_por_hora = float(salario_por_hora)  # Convertir a float
            except ValueError:
                messages.error(request, 'El valor del salario por hora debe ser un número decimal.')
                return redirect('edit_employees')
        
        try:
            user.save()
            messages.success(request, 'Información del empleado actualizada correctamente.')
        except IntegrityError:
            messages.error(request, 'El código de barras ya está en uso. Por favor, elige otro.')
        
        return redirect('edit_employees')
    
    employees = CustomUser.objects.all()
    return render(request, 'edit_employees.html', {'employees': employees})


def registrar_asistencia(request, cbarra):
    user = get_object_or_404(CustomUser, cbarra=cbarra)
    registro = RegistroAsistencia.objects.filter(user=user, salida__isnull=True).first()

    if registro:
        registro.registrar_salida()
        return HttpResponse(f"Salida registrada para {user.email}")
    else:
        RegistroAsistencia.objects.create(user=user, entrada=timezone.now())
        return HttpResponse(f"Entrada registrada para {user.email}")

@login_required
def generar_codigo_barras(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if user.cbarra:
        code = barcode.get('code128', str(user.cbarra), writer=ImageWriter())
        buffer = BytesIO()
        code.write(buffer)
        user.barcode_image.save(f'{user.cbarra}.png', ContentFile(buffer.getvalue()), save=False)
        user.save()
    return redirect('edit_employees')

@login_required
def ver_codigos_barras(request):
    buscar = request.GET.get('buscar')
    if buscar:
        employees = CustomUser.objects.filter(
            Q(id__icontains=buscar) | 
            Q(username__icontains=buscar) | 
            Q(cbarra__icontains=buscar)
        )
    else:
        employees = CustomUser.objects.all()
    return render(request, 'ver_codigos_barras.html', {'employees': employees})

# Vista para exportar a Excel
@login_required
def export_excel(request):
    fecha_inicio = request.session.get('fecha_inicio')
    fecha_fin = request.session.get('fecha_fin')

    if fecha_inicio and fecha_fin:
        registros = RegistroAsistencia.objects.filter(
            entrada__date__range=[fecha_inicio, fecha_fin]
        ).order_by('-entrada')
    elif fecha_inicio:
        registros = RegistroAsistencia.objects.filter(
            entrada__date=fecha_inicio
        ).order_by('-entrada')
    else:
        registros = RegistroAsistencia.objects.all().order_by('-entrada')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="registro_asistencia.csv"'

    writer = csv.writer(response)
    writer.writerow(['Usuario', 'Entrada', 'Salida', 'Asistencia Completa'])

    for registro in registros:
        writer.writerow([registro.user.email, registro.entrada, registro.salida, '1' if registro.completo else '0'])

    return response

# Vista para exportar a PDF
@login_required
def export_pdf(request):
    fecha_inicio = request.session.get('fecha_inicio')
    fecha_fin = request.session.get('fecha_fin')

    if fecha_inicio and fecha_fin:
        registros = RegistroAsistencia.objects.filter(
            entrada__date__range=[fecha_inicio, fecha_fin]
        ).order_by('-entrada')
    elif fecha_inicio:
        registros = RegistroAsistencia.objects.filter(
            entrada__date=fecha_inicio
        ).order_by('-entrada')
    else:
        registros = RegistroAsistencia.objects.all().order_by('-entrada')

    template_path = 'registro_asistencia_pdf.html'
    context = {'registros': registros}
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="registro_asistencia.pdf"'

    template = get_template(template_path)
    html = template.render(context)
    pisa_status = pisa.CreatePDF(io.BytesIO(html.encode('UTF-8')), dest=response)

    if pisa_status.err:
        return HttpResponse('Hubo un error al generar el PDF')

    return response

from django.urls import path
from myapp import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home_view, name='home'),
    path('home/', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('end_work_session/<int:session_id>/', views.end_work_session, name='end_work_session'),
    path('admin_login/', views.admin_login_view, name='admin_login'),
    path('edit_employees/', views.edit_employees_view, name='edit_employees'),
    path('registrar-asistencia/<int:cbarra>/', views.registrar_asistencia, name='registrar_asistencia'),
    path('generar-codigo-barras/<int:user_id>/', views.generar_codigo_barras, name='generar_codigo_barras'),
    path('ver-codigos-barras/', views.ver_codigos_barras, name='ver_codigos_barras'),
    path('asistencia/', views.asistencia_view, name='asistencia'),
    path('export_excel/', views.export_excel, name='export_excel'),  # Añadir ruta para exportar a Excel
    path('export_pdf/', views.export_pdf, name='export_pdf'),  # Añadir ruta para exportar a PDF
    path('delete_employee/<int:employee_id>/', views.delete_employee, name='delete_employee'),  # Añadir ruta para eliminar empleado
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, WorkSession

class RegisterForm(UserCreationForm):
    email = forms.EmailField(label=_("Correo electrónico"))
    cargo = forms.CharField(max_length=150, label=_("Cargo"))
    horas = forms.IntegerField(label=_("Horas"))
    salario_por_hora = forms.DecimalField(max_digits=10, decimal_places=2, label=_("Salario por hora"))

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'cargo', 'horas', 'salario_por_hora', 'password1', 'password2')
        labels = {
            'username': _('Nombre de usuario'),
        }
        help_texts = {
            'username': _('Requerido. 150 caracteres o menos. Letras, dígitos y @/./+/-/_ solamente.'),
        }
        error_messages = {
            'username': {
                'required': _("Este campo es obligatorio."),
                'max_length': _("El nombre de usuario no puede tener más de 150 caracteres."),
            },
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("Las contraseñas no coinciden."))
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class LoginForm(forms.Form):
    email = forms.EmailField(label=_("Correo electrónico"))
    password = forms.CharField(widget=forms.PasswordInput, label=_("Contraseña"))

class WorkSessionForm(forms.ModelForm):
    class Meta:
        model = WorkSession
        fields = []

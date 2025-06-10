
from django import forms
from .models import UsuarioRegistro
import re

class RegistroForm(forms.ModelForm):
    confirmar_clave = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = UsuarioRegistro
        fields = ['nombre', 'rut', 'correo', 'clave', 'confirmar_clave', 'tipo_usuario', 'razon_social']
        widgets = {
            'clave': forms.PasswordInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        correo = cleaned_data.get("correo")
        clave = cleaned_data.get("clave")
        confirmar = cleaned_data.get("confirmar_clave")

        if not re.match(r'.+@(gmail|hotmail)\.com$', correo):
            raise forms.ValidationError("El correo debe ser @gmail.com o @hotmail.com")

        if clave != confirmar:
            raise forms.ValidationError("Las contraseñas no coinciden.")

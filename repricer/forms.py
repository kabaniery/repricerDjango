from django import forms
from django.contrib.auth.forms import UserCreationForm

from repricer.models import Client


class LoginForm(forms.Form):
    login = forms.IntegerField(label='Client ID')
    password = forms.CharField(
        widget=forms.PasswordInput(),
        label='Api Key'
    )


class RegisterForm(forms.Form):
    login = forms.IntegerField(label='Client ID')
    password = forms.CharField(widget=forms.PasswordInput(),
                               label='Api Key')
    shop_url = forms.CharField(label="Адрес магазина")


class FileForm(forms.Form):
    file = forms.FileField()
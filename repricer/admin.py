from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path

from repricer.models import Client
import os

# Register your models here.
admin.site.register(Client)


class ServerAdmin(admin.ModelAdmin):
    def restart_server(self):
        os.system("sudo reboot")
        return HttpResponseRedirect("../")

    def get_urls(self):
        urls = super().get_urls()
        add = [
            path('restart-server/', self.restart_server, name='restart-server')
        ]
        return add + urls

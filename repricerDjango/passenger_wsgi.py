"""
WSGI config for repricerDjango project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
import os, sys
sys.path.insert(0, '/var/www/u2708090/data/repricerDjango')
sys.path.insert(1, '/var/www/u2708090/data/repricerVenv/lib/python3.10/site-packages')
os.environ['DJANGO_SETTINGS_MODULE'] = 'repricerDjango.settings'

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repricerDjango.settings')

application = get_wsgi_application()

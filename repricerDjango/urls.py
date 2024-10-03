"""
URL configuration for repricerDjango project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from repricer.views import start_page, login_view, register_view, get_data, change_price, load_from_ozon, \
    get_product_count, load_from_file, log_out
from repricerDjango import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', start_page, name='index'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('get_data/', get_data, name='get_data'),
    path('change_price/', change_price, name='change_price'),
    path('load_ozon', load_from_ozon, name='load_ozon'),
    path('get_count/', get_product_count, name='get_count'),
    path('load_csv/', load_from_file, name='load_csv'),
    path('logout/', log_out, name='logout'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
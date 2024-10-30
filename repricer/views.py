import json
import logging

import openpyxl
from django.apps import apps
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from redis import Redis

from repricer.forms import LoginForm, RegisterForm
from repricer.models import Client, Product
from scripts.Driver import get_request
from scripts.ShopInfo import check_shop_info





# Create your views here.
@login_required
def start_page(request):
    client = request.user
    assert isinstance(client, Client)
    try:
        return render(request, 'index.html', {'avatar_path': client.shop_avatar.url, 'shop_name': client.shop_name})
    except ValueError:
        return render(request, 'index.html', {'avatar_path': '',
                                              'shop_name': client.shop_name})  # TODO: Проставить путь к статическому аватару


def register_view(request):
    if request.method == 'POST':
        client_id = request.POST['login']
        api_key = request.POST['password']
        shop_url = request.POST['shop_url']

        if check_shop_info(client_id, api_key):
            new_password = make_password(api_key)
            new_client = Client(username=client_id, password=new_password, api_key=api_key)
            new_client.save()
            login(request, new_client)

            broker: Redis = apps.get_app_config("repricer").repricer
            broker.lpush("register", f"{client_id};{shop_url}")

            return redirect('index')
        else:
            messages.error(request, "Данные магазина неверны")
            return render(request, 'form_template.html', {'form': RegisterForm(), 'form_type': "Регистрация"})
    else:
        form = RegisterForm()
        return render(request, 'form_template.html', {'form': form, 'form_type': "Регистрация"})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['login']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')
            else:
                messages.error(request, "Пользователь не найден")

        else:
            messages.error(request, "Неправильный формат ввода")

    form = LoginForm()
    return render(request, 'form_template.html', {'form': form, 'form_type': "Авторизация"})


@login_required
def get_data(request):
    client = request.user
    assert isinstance(client, Client)

    ready_products = Product.objects.filter(shop=client)
    return render(request, "products_list.html", {'products': ready_products[:450]})


@login_required
def change_price(request):
    if request.method == 'POST':
        client = request.user
        assert isinstance(client, Client)

        old_val = dict()
        new_val = dict()
        for key, value in request.POST.items():
            if str(key)[:3] == 'old':
                old_val[str(key)[3::]] = value
            elif str(key)[:3] == 'new':
                new_val[str(key)[3::]] = value
        editing_orders = dict()
        for key, value in new_val.items():
            if old_val[key] != value:
                editing_orders[key] = [old_val[key], value]

        if len(editing_orders.keys()) == 0:
            messages.warning(request, "Нет цен для замены")
        else:
            broker: Redis = apps.get_app_config("repricer").repricer
            broker.lpush("changer", f"{client.username};;{json.dumps(editing_orders)}")
    return redirect('get_data')


@login_required
def load_from_ozon(request):
    client = request.user
    assert isinstance(client, Client)

    if not client.product_blocked:
        client.product_blocked = True
        client.last_product = None
        client.save()

        Product.objects.filter(shop=client).update(to_removal=True)
        broker: Redis = apps.get_app_config('repricer').broker
        broker.lpush("parser", client.username)

        return HttpResponse("Success", status=200)
    else:
        return HttpResponse("You are already added", status=400)


@login_required
def get_product_count(request):
    client = request.user
    assert isinstance(client, Client)

    products = Product.objects.filter(shop=client)
    return JsonResponse({'count': products.count()})


@login_required
def load_from_file(request):
    if request.method == 'POST':
        client = request.user
        assert isinstance(client, Client)

        with open(f"tmp/{client.username}.xlsx", 'wb') as f:
            for chunk in request.FILES['csv_input'].chunks():
                f.write(chunk)

        workbook = openpyxl.load_workbook(f"tmp/{client.username}.xlsx")
        sheet = workbook.active

        mass = dict()
        updated_products = list()

        for row in sheet.iter_rows(min_row=2, values_only=True):
            row_values = row[:2]
            if len(row_values) < 2:
                continue
            offer_id = row_values[0]
            if isinstance(offer_id, float):
                offer_id = str(int(offer_id))
            else:
                offer_id = str(offer_id)

            try:
                price = int(row_values[1])
            except ValueError:
                continue
            except TypeError:
                continue
            try:
                product = Product.objects.get(shop=client, offer_id=offer_id)
                product.needed_price = price
                updated_products.append(product)
            except Exception as e:
                continue
            if product.price != price:
                mass[offer_id] = [product.price, price]

        Product.objects.bulk_update(updated_products, ['needed_price'])
        broker: Redis = apps.get_app_config("repricer").repricer
        broker.lpush("changing", f"{client.username};;{json.dumps(mass)}")
    return redirect('index')


@login_required
def log_out(request):
    logout(request)
    return redirect('login')


@login_required
def queue_ended(request):
    client = request.user
    assert isinstance(client, Client)
    return JsonResponse({'answer': client.product_blocked})

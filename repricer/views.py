import time
import logging
import openpyxl
import requests
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect

from ChromeController.ProcessManager import Manager
from repricer.forms import LoginForm, RegisterForm
from repricer.models import Client, Product
from scripts.Driver import get_request


def is_old_price_correct(old_price, price):
    if old_price == 0:
        return True
    if price < 400:
        return old_price - price > 20
    elif price < 10000:
        return price / old_price < 0.95
    else:
        return old_price - price > 500


# products: {'offer-id': (old_price, new_price, new_gray_price)}
def changing_price(client: Client, products, last_time=False):
    headers = {
        'Client-Id': client.username,
        'Api-Key': client.api_key
    }
    data = {
        'filter': {
            'offer_id': list(products.keys())
        },
        'limit': str(len(products.keys()))
    }
    print(headers)
    print("____________________")
    print(data)
    response = get_request("https://api-seller.ozon.ru/v4/product/info/prices", headers, data)
    if response.status_code == 200:
        prices = list()
        for item in response.json()['result']['items']:
            # old_gray = int(float((request.POST['gray'+str(item['offer_id'])])))
            new_green = int(float(products[item['offer_id']][1]))
            fact_price = int(float(item['price']['price']))
            old_green = int(float(products[item['offer_id']][0]))
            new_price = int(new_green * fact_price / old_green)
            if item['offer_id'] == '77103':
                print('setted price -', new_price)
            if is_old_price_correct(float(item['price']['old_price']), new_price):
                old_price = item['price']['old_price']
            else:
                old_price = str(int(float(item['price']['old_price']) * new_price / fact_price))
            actual_data = {
                'auto_action_enabled': 'UNKNOWN',
                'currency_code': item['price']['currency_code'],
                'min_price': str(new_price - 1),
                'offer_id': item['offer_id'],
                'old_price': old_price,
                'price': str(new_price),
                'price_strategy_enabled': 'UNKNOWN',
                'product_id': item['product_id']
            }
            prices.append(actual_data)
        new_data = {
            'prices': prices
        }
        response = get_request('https://api-seller.ozon.ru/v1/product/import/prices', headers, new_data)
        if response.status_code == 200:
            if last_time:
                try:
                    for key, value in products.items():
                        try:
                            product = Product.objects.get(shop=client, offer_id=key)
                            product.price = value[1]
                            product.save()
                        except:
                            print("Error reparse for product", key, "user", client.username)
                    return "Ok"
                except ValueError as e:
                    print(e)
                    print(products)
            manager = Manager.get_instance()
            for key, value in products.items():
                manager.correct_product(client.username, client.api_key, key, value[1])
        else:
            print("error on edit", response.text)
    else:
        print("error", response.text)
    return "Ok"


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
        manager = Manager.get_instance()
        result = manager.push_request(shop_url, client_id, api_key)
        if result['status']:
            new_password = make_password(api_key)
            new_client = Client(username=client_id, password=new_password,
                                shop_name=client_id, api_key=api_key)
            new_client.save()
            login(request, new_client)
            return redirect('index')
        else:
            logging.getLogger("django").error("Can't register user:", result['message'])
            messages.error(request, result['message'])
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
                product = Product.objects.get(shop=client, offer_id=key)
                editing_orders[key] = [old_val[key], value, 0]
        if len(editing_orders.keys()) == 0:
            messages.warning(request, "Нет цен для замены")
        else:
            changing_price(client, editing_orders)
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
        print("product count", len(Product.objects.filter(shop=client)))
        header = {
            "Client-Id": client.username,
            'Api-Key': client.api_key
        }
        body = {
            'filter':
                {
                    'visibility': 'VISIBLE'
                },
            'limit': 1000
        }
        all_data = get_request("https://api-seller.ozon.ru/v2/product/list", header, body)
        if all_data.status_code == 200:
            manager = Manager.get_instance()
            print("Overall size is", len(all_data.json()['result']['items']))
            last_offer_id = None
            for item in all_data.json()['result']['items']:
                manager.add_product(client.username, client.api_key, item['offer_id'])
                last_offer_id = item['offer_id']
            print("Getted last offer id", last_offer_id)
            if last_offer_id is not None:
                client.last_product = str(last_offer_id)
                client.save()
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
        print("file opened")
        workbook = openpyxl.load_workbook(f"tmp/{client.username}.xlsx")
        sheet = workbook.active
        mass = dict()
        updated_products = list()
        for row in sheet.iter_rows(min_row=2, values_only=True):
            print(row)
            row_values = row[:2]
            if len(row_values) < 2:
                continue
            offer_id = row_values[0]
            if isinstance(offer_id, float):
                offer_id = str(int(offer_id))
            else:
                offer_id = str(offer_id)
            price = 0
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
                mass[offer_id] = [product.price, price]
                print(product.offer_id, product.needed_price)
            except Exception as e:
                continue
            if product.price != price:
                mass[offer_id] = [product.price, price]
        Product.objects.bulk_update(updated_products, ['needed_price'])
        changing_price(client, mass)
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

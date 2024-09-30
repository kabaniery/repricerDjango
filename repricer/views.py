from itertools import product

import requests
from django.apps import apps
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse
from django.shortcuts import render, redirect

from ChromeController.ProcessManager import Manager
from repricer.forms import LoginForm, RegisterForm
from repricer.models import Client, Product
from scripts.ShopInfo import get_shop_infos


# Create your views here.
@login_required
def start_page(request):
    client = request.user
    assert isinstance(client, Client)
    try:
        return render(request, 'index.html', {'avatar_path': client.shop_avatar.url, 'shop_name': client.shop_name})
    except ValueError:
        return render(request, 'index.html', {'avatar_path': '', 'shop_name': client.shop_name}) #TODO: Проставить путь к статическому аватару


def register_view(request):
    if request.method == 'POST':
        client_id = request.POST['login']
        api_key = request.POST['password']
        shop_url = request.POST['shop_url']
        manager = Manager.get_instance()
        result = manager.push_request(shop_url, client_id, api_key)
        if result['status']:
            new_password = make_password(api_key)
            new_client = Client(username=client_id, password=new_password, shop_address=shop_url,
                                shop_name=client_id, api_key=api_key)
            new_client.save()
            login(request, new_client)
            return redirect('index')
        else:
            print(result['message'])
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
    return render(request, "products_list.html", {'products': ready_products})


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
                editing_orders[key] = value
        if len(editing_orders.keys()) == 0:
            messages.warning(request, "Нет цен для замены")
        else:
            headers = {
                'Client-Id': client.username,
                'Api-Key': client.api_key
            }
            data = {
                'filter': {
                    'offer_id': list(editing_orders.keys())
                },
                'limit': len(editing_orders.keys())
            }
            response = requests.post("https://api-seller.ozon.ru/v4/product/info/prices", headers=headers, json=data)
            if response.status_code == 200:
                prices = list()
                for item in response.json()['result']['items']:
                    #old_gray = int(float((request.POST['gray'+str(item['offer_id'])])))
                    new_green = int(float(new_val[item['offer_id']]))
                    fact_price = int(float(item['price']['price']))
                    old_green = int(float(old_val[item['offer_id']]))
                    new_price = int(new_green * fact_price / old_green)
                    actual_data = {
                        'auto_action_enabled': 'UNKNOWN',
                        'currency_code': item['price']['currency_code'],
                        'min_price': str(new_price - 1),
                        'offer_id': item['offer_id'],
                        'old_price': '0',
                        'price': str(new_price),
                        'price_strategy_enabled': 'UNKNOWN',
                        'product_id': item['product_id']
                    }
                    prices.append(actual_data)
                new_data = {
                    'prices': prices
                }
                response = requests.post('https://api-seller.ozon.ru/v1/product/import/prices', headers=headers,
                                         json=new_data)
                if response.status_code == 200:
                    for item in prices:
                        product = Product.objects.get(shop=client, offer_id=item['offer_id'])
                        product.price = int(float(new_val[item['offer_id']]))
                        product.save()
                    messages.info(request, "Успешно")
                else:
                    messages.warning(request, "Ошибка " + response.text)
            else:
                messages.warning(request, "Не удалось получить информацию о ценах")
    return redirect('get_data')


@login_required
def load_from_ozon(request):
    client = request.user
    assert isinstance(client, Client)
    if True:
        client.product_blocked = True
        client.save()
        Product.objects.filter(shop=client).delete()
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

        all_data = requests.post("https://api-seller.ozon.ru/v2/product/list", headers=header, json=body)
        if all_data.status_code == 200:
            manager = Manager.get_instance()
            print("Overall size is", len(all_data.json()['result']['items']))
            for item in all_data.json()['result']['items']:
                manager.add_product(client.username, client.api_key, item['offer_id'])
        return HttpResponse("Success", status=200)
    else:
        return HttpResponse("You are already added", status=400)


# TODO: убрать
@login_required
def example(request):
    '''page_href = "https://www.ozon.ru/product/teleskop-sky-watcher-bk-p2001eq5-1517132768/"
    driver = get_driver()
    proc = SeleniumProcess()
    proc.find_price(page_href, driver)
    driver.close()'''
    client = request.user
    assert isinstance(client, Client)
    client.product_blocked = False
    client.save()
    return HttpResponse("hi")

@login_required
def get_product_count(request):
    client = request.user
    assert isinstance(client, Client)
    products = Product.objects.filter(shop=client)
    return HttpResponse(products.count())

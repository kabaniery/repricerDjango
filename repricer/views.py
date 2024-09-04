import requests
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect

from repricer.models import Client, Product
from repricer.forms import LoginForm, RegisterForm
from repricer.scripts.ozon_finder import get_shop_infos, get_driver, get_code
from repricer.scripts.web_manager import WebManager
from lxml import etree
from selenium.webdriver.common.by import By


# Create your views here.
@login_required
def start_page(request):
    client = request.user
    assert isinstance(client, Client)
    return render(request, 'index.html', {'avatar_path': client.shop_avatar.url, 'shop_name': client.shop_name})


def register_view(request):
    if request.method == 'POST':
        client_id = request.POST['login']
        api_key = request.POST['password']
        shop_url = request.POST['shop_url']
        result = get_shop_infos(client_id, api_key, shop_url)
        if result['status']:
            new_password = make_password(api_key)
            new_client = Client(username=client_id, password=new_password, shop_address=shop_url,
                                shop_name=result['shop_name'])
            new_client.save()
            new_client.shop_avatar.save(result['avatar_name'], result['avatar_path'])
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
    if not client.product_blocked:
        ready_products = Product.objects.filter(shop=client)
        return render(request, "products_list.html", {'products': ready_products})
    else:
        messages.error(request, "Загрузка данных ещё не завершилась")
        return redirect('index')


@login_required
def change_price(request):
    if request.method == 'POST':
        client = request.user
        assert isinstance(client, Client)
        old_val = dict()
        new_val = dict()
        for key, value in request.POST.items:
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
                'Api-Key': client.password
            }
            data = {
                'filter': {
                    'offer_id': list(editing_orders.keys())
                },
                'limit': len(editing_orders.keys())
            }
            response = requests.post("https://api-seller.ozon.ru/v4/product/info/prices", headers=headers, json=data)
            green_coeff = dict()
            if response.status_code == 200:
                prices = list()
                for item in response.json()['result']['items']:
                    green_coeff[item['offer_id']] = old_val[item['offer_id']] / item['price']['marketing_price']
                    new_price = int(new_val[item['offer_id']] * item['price']['price'] / old_val[item['offer_id']])
                    actual_data = {
                        'auto_action_enabled': 'UNKNOWN',
                        'currency_code': item['price']['currency_code'],
                        'min_price': str(int(new_price * 0.8)),
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
                    messages.info(request, "Успешно")
                else:
                    messages.warning(request, "Ошибка " + response.text)
            else:
                messages.warning(request, "Не удалось получить информацию о ценах")


@login_required
def load_from_ozon(request):
    client = request.user
    assert isinstance(client, Client)

    if not client.product_blocked:
        client.product_blocked = True
        client.save()
        WebManager.add_to_queue(client)
        return HttpResponse("Success", status=200)
    else:
        return HttpResponse("You are already added", status=400)


# TODO: убрать
def example(request):
    page_href = "https://www.ozon.ru/seller/elektromart-1590790/products/?miniapp=seller_1590790"
    driver = get_driver()
    code = get_code(driver, page_href)
    with open("block_name", "w") as temp:
        temp.write(driver.title)
    elem = driver.find_element(By.TAG_NAME, "html").find_element(By.TAG_NAME, "body").find_element(By.TAG_NAME, "div").find_element(By.TAG_NAME, "div")
    elem = elem.find_element(By.TAG_NAME, "div").find_elements(By.TAG_NAME, "div")
    elem[2].find_element(By.TAG_NAME, "button").click()
    print(elem[2].get_attribute("class"))
    driver.close()
    return HttpResponse(code)

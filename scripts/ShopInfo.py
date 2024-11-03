from scripts.Driver import get_request


# ВОЗВРАЩАЕТ ДАННЫЕ В UTF-8


def check_shop_info(client_id, api_key):
    headers = {
        'Client-Id': str(client_id),
        'Api-Key': api_key,
    }
    body = {
        'filter': dict(),
        'limit': 1
    }
    response = get_request("https://api-seller.ozon.ru/v2/product/list", headers, body)
    if response.status_code == 200:
        return True
    return False

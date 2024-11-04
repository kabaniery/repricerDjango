#!/bin/bash

DOMAIN="api-seller.ozon.ru"
OTHDOMAIN="ozon.ru"


GATEWAY="10.0.0.1"
INTERFACE="ens3"
SRC_IP="212.109.196.65"

IP_ADDRESSES=$(dig +short "$DOMAIN")

if [ -z "$IP_ADDRESSES" ]; then
  echo "Не удалось получить IP-адреса для домена $DOMAIN"
  exit 1
fi

for IP in $IP_ADDRESSES; do
  echo "Добавление маршрута для $IP"
  sudo ip route add "$IP" via "$GATEWAY" dev "$INTERFACE" onlink src "$SRC_IP"
done

# Получение IP-адресов для OTHDOMAIN
IP_ADDRESSES_OTHDOMAIN=$(dig +short "$OTHDOMAIN")

if [ -z "$IP_ADDRESSES_OTHDOMAIN" ]; then
  echo "Не удалось получить IP-адреса для домена $OTHDOMAIN"
  exit 1
fi

for IP in $IP_ADDRESSES_OTHDOMAIN; do
  echo "Добавление маршрута для $IP (домен $OTHDOMAIN)"
  sudo ip route add "$IP" via "$GATEWAY" dev "$INTERFACE" onlink src "$SRC_IP"
done

source venv/bin/activate
python windowServer.py

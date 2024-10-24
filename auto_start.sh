#!/bin/bash

DOMAIN="api-seller.ozon.ru"

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


source venv/bin/activate
python windowServer.py

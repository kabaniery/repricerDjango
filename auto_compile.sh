#!/bin/bash

# Обновляем список пакетов
sudo apt update

# Устанавливаем Python и необходимые пакеты
sudo apt install -y python3 python3-venv python3-pip

# Устанавливаем MySQL
sudo apt install -y mysql-server

# Настраиваем MySQL (можно использовать MySQL_secure_installation для первоначальной настройки)
sudo mysql_secure_installation

# Создаем схему repricer и пользователя repricer-manager с правами доступа
sudo mysql -e "CREATE DATABASE repricer;"
sudo mysql -e "CREATE USER 'repricer-manager'@'localhost' IDENTIFIED BY 'repricerpassword';"
sudo mysql -e "GRANT ALL PRIVILEGES ON repricer.* TO 'repricer-manager'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

# Устанавливаем Google Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable

# Устанавливаем ChromeDriver
CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | sed 's/\.[0-9]*$//')
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION")
wget -N "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
rm chromedriver_linux64.zip

# Создаем виртуальное окружение и активируем его
python -m venv venv
source venv/bin/activate

# Устанавливаем зависимости из requirements.txt
python -m pip install -r requirements.txt

# Выполняем команды управления Django
python manage.py collectstatic --noinput
python manage.py migrate

# Запускаем windowServer.py
python windowServer.py


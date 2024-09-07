FROM python:3.10

# Установка ключа и добавление репозитория для Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'

# Обновление и установка необходимых пакетов
RUN apt-get -y update && \
    apt-get install -y \
    google-chrome-stable \
    xfce4 \
    xfce4-goodies \
    xorg \
    dbus-x11 \
    x11-xserver-utils \
    xinit

# Установка переменной окружения для дисплея
ENV DISPLAY=:99

# Установка рабочей директории
WORKDIR /app

# Копирование содержимого приложения
COPY . /app

# Установка зависимостей Python
RUN python -m pip install -r requirements.txt

# Запуск X-сервера и приложения
CMD ["sh", "-c", "startx & sleep 5 && python manage.py migrate && python manage.py runserver 127.0.0.1:8000"]

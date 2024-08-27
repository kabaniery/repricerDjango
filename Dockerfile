FROM python:3.10

# Это chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get -y update
RUN apt-get install -y google-chrome-stable

# Это SQLite
RUN apt-get update && apt-get install -y sqlite3

ENV DISPLAY=:99

WORKDIR /app
COPY . /app

RUN python -m pip install -r requirements.txt
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:80"]
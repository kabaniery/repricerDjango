FROM python:3.10

RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get -y update
RUN apt-get install -y google-chrome-stable

ENV DISPLAY=:99

WORKDIR /app
COPY . /app

RUN python -m pip install -r requirements.txt
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 127.0.0.1:8000"]
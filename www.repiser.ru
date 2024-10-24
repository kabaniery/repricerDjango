server {
    listen 80;
    server_name www.repiser.ru;

    # Путь до корня вашего проекта Django
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Обслуживание статических файлов
    location /static/ {
        alias /var/www/repricerDjango/static/;
        expires 2h;
        add_header Cache-Control "public, no-transform";
    }

    # Обслуживание медиа-файлов
    location /media/ {
        alias /var/www/repricerDjango/media/;
        expires 2h;
        add_header Cache-Control "public, no-transform";
    }

    # Настройка для улучшенной безопасности (опционально)
    client_max_body_size 100M;
}
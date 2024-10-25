server {
    listen 80;
    server_name www.repiser.ru;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/repricerDjango/staticfiles/;
        expires 2h;
        add_header Cache-Control "public, no-transform";
    }

    location /media/ {
        alias /var/www/repricerDjango/media/;
        expires 2h;
        add_header Cache-Control "public, no-transform";
    }

    client_max_body_size 100M;
}
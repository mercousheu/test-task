# Test Task

## Run in local mode:
1. Create in root directory file named `.env`
2. Fill this file with values according to the example below
``
POSTGRES_USER=postgres
POSTGRES_PASSWORD=testPassword
POSTGRES_HOST=postgres-host
POSTGRES_DB=test_base
DATABASE_URL=postgresql+asyncpg://postgres:testPassword@postgres-host/test_base
HOST=127.0.0.1``
where the `HOST` is the public IP address of your server
3. run `docker-compose up --build`

## Deploying behind the Nginx

1. Do all the steps listed above
2. Create virtual nginx host
3. Put the following code into the host config
```server {
    server_name  <Your server IP>;
    charset UTF-8;
    listen 80;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_redirect     off;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Host $server_name;
        proxy_read_timeout 9000;
        proxy_connect_timeout 9000;
        proxy_send_timeout 9000;
        send_timeout 9000;
    }
}
```
4. Link created host to enabled sites
5. Restart nginx

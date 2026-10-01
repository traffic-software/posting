#!/usr/bin/env bash
set -euo pipefail

mode="${1:-setup}"
if [ "$EUID" -ne 0 ]; then
    echo 'Nginx setup requires root or passwordless sudo' >&2
    exit 1
fi
. /etc/os-release
case "$ID" in
    ubuntu|debian) ;;
    *) echo 'Nginx setup supports Ubuntu and Debian only' >&2; exit 1 ;;
esac
command -v apt-get >/dev/null
if [ "$mode" = preflight ]; then
    exit 0
fi
if [ "$mode" != setup ]; then
    echo 'Usage: setup-nginx.sh [preflight|setup]' >&2
    exit 1
fi
read -r email
if [[ ! "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
    echo 'A valid LETSENCRYPT_EMAIL is required on stdin' >&2
    exit 1
fi
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
template="$script_dir/nginx/webagent.conf"
test -f "$template"
if ! command -v nginx >/dev/null || ! command -v certbot >/dev/null; then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y nginx certbot
fi
nginx -t
install -d -m 755 /var/www/posting-acme /etc/nginx/sites-available /etc/nginx/sites-enabled
site=/etc/nginx/sites-available/posting-webagent.conf
link=/etc/nginx/sites-enabled/posting-webagent.conf
# Only manage our own site; refuse to replace a foreign link or regular file.
if [ -e "$link" ] || [ -L "$link" ]; then
    if [ ! -L "$link" ] || [ "$(readlink "$link")" != "$site" ]; then
        echo "Refusing to replace existing $link" >&2
        exit 1
    fi
fi
backup="$(mktemp -d)"
had_site=false
had_link=false
if [ -e "$site" ]; then
    cp -a "$site" "$backup/site"
    had_site=true
fi
if [ -L "$link" ]; then
    had_link=true
fi
restore_on_failure() {
    status=$?
    if [ "$status" -ne 0 ]; then
        echo 'Nginx setup failed; restoring previous application site' >&2
        if "$had_site"; then
            cp -a "$backup/site" "$site"
        else
            rm -f "$site"
        fi
        if ! "$had_link"; then
            rm -f "$link"
        fi
        if nginx -t; then
            systemctl reload nginx || true
        fi
    fi
    rm -rf "$backup"
}
trap restore_on_failure EXIT
cert=/etc/letsencrypt/live/webagent.elgrowth.com
if [ ! -f "$cert/fullchain.pem" ] || [ ! -f "$cert/privkey.pem" ]; then
    cat > "$site" <<'HTTP'
server {
    listen 80;
    listen [::]:80;
    server_name webagent.elgrowth.com;
    location ^~ /.well-known/acme-challenge/ {
        root /var/www/posting-acme;
    }
    location / {
        return 503;
    }
}
HTTP
    ln -sfn "$site" "$link"
    nginx -t
    systemctl enable --now nginx
    systemctl reload nginx
else
    install -m 644 "$template" "$site"
    ln -sfn "$site" "$link"
    nginx -t
    systemctl enable --now nginx
    systemctl reload nginx
fi
# Certbot reuses a valid certificate, renewing only when necessary.
certbot certonly --non-interactive --agree-tos --email "$email" \
    --webroot --webroot-path /var/www/posting-acme \
    --cert-name webagent.elgrowth.com -d webagent.elgrowth.com --keep-until-expiring
install -m 644 "$template" "$site"
ln -sfn "$site" "$link"
nginx -t
systemctl enable --now nginx
systemctl reload nginx
install -d -m 755 /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/posting-reload-nginx <<'HOOK'
#!/bin/sh
set -eu
nginx -t
systemctl reload nginx
HOOK
chmod 755 /etc/letsencrypt/renewal-hooks/deploy/posting-reload-nginx
systemctl enable --now certbot.timer
echo 'HTTPS configured for https://webagent.elgrowth.com'

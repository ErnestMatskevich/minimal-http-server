#!/bin/sh
set -eu

if [ -z "${CUSTOM_SERVER_URL:-}" ]; then
    echo "CUSTOM_SERVER_URL is not set"
    exit 1
fi

if [ -z "${NGINX_SERVER_URL:-}" ]; then
    echo "NGINX_SERVER_URL is not set"
    exit 1
fi

echo "=== Custom Python Server ==="
ab -n 1000 -c 10 "$CUSTOM_SERVER_URL"

echo
echo "=== nginx ==="
ab -n 1000 -c 10 "$NGINX_SERVER_URL"

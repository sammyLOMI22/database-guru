# ---- Build Stage ----
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

# ---- Production Stage ----
FROM nginx:1.25-alpine

# Remove default nginx config (custom config mounted via docker-compose)
RUN rm /etc/nginx/conf.d/default.conf

# Create non-root nginx user and adjust permissions
RUN addgroup -g 1001 -S nginxuser && \
    adduser -u 1001 -S -G nginxuser nginxuser && \
    mkdir -p /var/cache/nginx/client_temp \
             /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp \
             /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp \
             /tmp/nginx && \
    chown -R nginxuser:nginxuser /var/cache/nginx /etc/nginx/conf.d /tmp/nginx

# Override main nginx.conf to use non-root-compatible paths
RUN sed -i 's|/var/run/nginx.pid|/tmp/nginx/nginx.pid|g' /etc/nginx/nginx.conf && \
    sed -i '/^user /d' /etc/nginx/nginx.conf

# Copy built assets
COPY --from=builder --chown=nginxuser:nginxuser /app/dist /usr/share/nginx/html

# Remove setuid/setgid binaries
RUN find / -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true

USER nginxuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:3000/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

FROM node:24-alpine AS build
WORKDIR /app
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web/ .
RUN npm run build

FROM nginxinc/nginx-unprivileged:stable-alpine
COPY infrastructure/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/aegis-web/browser /usr/share/nginx/html
EXPOSE 8080

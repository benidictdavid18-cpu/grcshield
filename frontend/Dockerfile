# Three stages. `docker compose up` (with the dev override) runs the `dev` stage: the
# Vite server with hot reload and the source bind-mounted. The base compose file and CI
# build the `serve` stage: a static bundle behind nginx, which also proxies /api to the
# API container and sets the page's own security headers.

FROM node:20-alpine AS deps
WORKDIR /app
# The lockfile is mandatory. `npm ci` refuses to run without one, which is the point:
# a build that resolves versions on the day it runs is a build that changes on its own.
COPY package.json package-lock.json ./
RUN npm ci

FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

FROM deps AS build
COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS serve
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY security-headers.conf /etc/nginx/security-headers.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

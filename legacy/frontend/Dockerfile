# Multi-stage build: compile the Procure CRM SPA, then serve via nginx.
# Targets Zeabur Docker. Independent of TanStack Start SSR / Cloudflare Workers.
# rev 2 — force Zeabur to clone fresh after webhook miss

# ── Stage 1: build the SPA bundle ───────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

# Vite reads VITE_* env vars at build time. Default points at the deployed
# Zeabur backend; override via --build-arg or Zeabur's "build args" UI.
ARG VITE_SHADOWBUYER_URL=https://shadowbuyer.zeabur.app
ENV VITE_SHADOWBUYER_URL=$VITE_SHADOWBUYER_URL

COPY package.json package-lock.json* bun.lock* ./
# Repo uses bun (bun.lock present, no package-lock.json). npm install works
# fine from package.json + dynamically resolves a lockfile.
RUN npm install --no-audit --no-fund --legacy-peer-deps

COPY . .
RUN npm run build:spa

# ── Stage 2: serve static assets ────────────────────────────────────────────
FROM nginx:1.27-alpine
COPY --from=builder /app/dist-spa /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Zeabur injects $PORT; default 8080 for local docker run.
ENV PORT=8080
EXPOSE 8080
CMD ["/bin/sh", "-c", "sed -i \"s/listen 8080/listen ${PORT}/\" /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]

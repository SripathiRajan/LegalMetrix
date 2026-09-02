# Stage 1: Build React SPA bundle with Vite & Node 20
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package manifests and install dependencies
COPY package*.json ./
RUN npm ci

# Copy full source tree and build static bundle
COPY . .
RUN npm run build

# Stage 2: Production Web Server with Nginx Alpine
FROM nginx:1.25-alpine AS runner

# Remove default nginx static web pages
RUN rm -rf /usr/share/nginx/html/*

# Copy build artifacts from stage 1
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration for SPA routing and API reverse proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

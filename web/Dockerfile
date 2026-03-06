FROM node:20-alpine AS builder
WORKDIR /app

# Enable corepack for modern package managers, though we use npm here
RUN corepack enable

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ============================================
# Stage 2: Serve static files with Nginx
# ============================================
FROM nginx:alpine

# Copy the static export from the builder stage
COPY --from=builder /app/out /usr/share/nginx/html

# Replace default Nginx configuration with our custom proxy setup
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]

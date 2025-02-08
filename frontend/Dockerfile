# Production Dockerfile: frontend/Dockerfile

# Stage 1: Build the frontend
FROM node:16-alpine AS build

# Set working directory
WORKDIR /app

ENV REACT_APP_API_BASE_URL=http://localhost:8000/api

# Install dependencies
COPY package.json package-lock.json ./
RUN npm install

# Copy source code
COPY . .

# Build the frontend
RUN npm run build

# Stage 2: Serve the frontend with Nginx
FROM nginx:stable-alpine

# Remove default Nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy the build output to Nginx's html directory
COPY --from=build /app/build /usr/share/nginx/html

# (Optional) Copy custom Nginx configuration if needed
# COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]

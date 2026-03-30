# NB The context is './frontend'
# Stage 1: Build the frontend
FROM node:20-alpine AS build
WORKDIR /app

# BEFORE: COPY ./frontend/package.json ./
# AFTER: , so the path is just 'package.json'
COPY package.json package-lock.json ./

RUN npm install

# BEFORE: COPY ./frontend ./
# AFTER: The context is now './frontend', so we copy everything from its root.
COPY . .

ARG REACT_APP_API_BASE_URL
ENV REACT_APP_API_BASE_URL=$REACT_APP_API_BASE_URL

RUN npm run build

# Stage 2: Serve the frontend with Nginx
FROM nginx:stable-alpine
RUN rm -rf /usr/share/nginx/html/*
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

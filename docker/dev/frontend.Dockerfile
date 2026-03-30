# Use Node.js base image for local development
FROM node:20-alpine

# Set working directory
WORKDIR /app

# 1. Copy only package manifests first to leverage Docker caching.
# This assumes the build context is the project root.
COPY ./frontend/package.json ./frontend/package-lock.json ./

# 2. Install dependencies. This layer will only be re-run if you change package.json.
RUN npm install

# 3. Copy the rest of the source code.
# In development, this is less important because the volume mount will
# override it, but it's good practice for a complete image.
COPY ./frontend ./

# Expose React's default development port
EXPOSE 3000

# Start the React app in development mode
CMD ["npm", "start"]

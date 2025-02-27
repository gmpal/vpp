# Use Node.js base image for local development
FROM node:16-alpine

# Set working directory
WORKDIR /app

# Install dependencies
COPY ./frontend/package.json ./frontend/package-lock.json ./
RUN npm install

# Copy all source code for hot reloading
COPY ./frontend .

# Expose React's default development port
EXPOSE 3000

# Start the React app in development mode
CMD ["npm", "start"]
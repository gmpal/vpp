# Use Node.js base image for local development
FROM node:16-alpine

# Set working directory
WORKDIR /app

# Install dependencies
COPY ./frontend .

RUN npm install

# Expose React's default development port
EXPOSE 3000

# Start the React app in development mode
CMD ["npm", "start"]
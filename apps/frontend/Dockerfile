FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Remove any host node_modules that may have been copied in
RUN rm -rf node_modules && npm install
# Development server — bind to all interfaces so Docker can expose the port
CMD ["npx", "vite", "--host", "0.0.0.0"]

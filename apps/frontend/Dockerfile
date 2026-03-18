FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Development server for Docker-Compose interoperability
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

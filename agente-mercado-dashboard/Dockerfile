FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
RUN npm install -g serve@14
COPY --from=build /app/dist /app/dist
EXPOSE 3000
CMD ["sh", "-c", "serve -s /app/dist -l ${PORT:-3000}"]

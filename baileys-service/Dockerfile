FROM node:20-alpine

# Dependências do sistema para sharp, etc.
RUN apk add --no-cache \
    git \
    openssh \
    python3 \
    make \
    g++ \
    cairo-dev \
    jpeg-dev \
    pango-dev \
    giflib-dev

WORKDIR /app

# Copia package.json / package-lock.json
COPY package*.json ./

# Instala só dependências de produção
RUN git config --global url."https://github.com/".insteadOf "git@github.com:"
RUN npm install --omit=dev

# Copia o restante do código (quando existir)
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]

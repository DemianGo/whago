FROM python:3.11-slim

WORKDIR /app

# Copia código e dependências
COPY ./app /app/app
COPY requirements.txt /app/

# Instala dependências e força instalação do driver asyncpg
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir asyncpg

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

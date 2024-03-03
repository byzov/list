FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

COPY ./app /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

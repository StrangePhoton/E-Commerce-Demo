FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    pkg-config \
    libpq-dev \
    libcairo2-dev \
    libjpeg-dev \
    libgif-dev \
    libpng-dev \
    libpangocairo-1.0-0 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "angelesyasam.wsgi:application", "--bind", "0.0.0.0:8000"]
FROM python:3.11-bookworm

WORKDIR /app

# Install System Dependencies
RUN apt-get update && apt-get install -y \
    libatlas-base-dev \
    gfortran \
    libgpiod2 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Offline Assets (Tailwind & Lucide)
RUN mkdir -p static/js && \
    wget -O static/js/tailwindcss.js https://cdn.tailwindcss.com && \
    wget -O static/js/lucide.js https://unpkg.com/lucide@latest

# Copy Application Code
# Copy Application Code
COPY . /app

RUN mkdir -p /data

CMD ["python", "main.py"]
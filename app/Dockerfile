FROM python:3.11-bookworm

WORKDIR /app

# ============================================
# LAYER 1: System Dependencies (rarely changes)
# ============================================
RUN apt-get update && apt-get install -y \
    libatlas-base-dev \
    libopenblas-dev \
    gfortran \
    libgpiod2 \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# LAYER 2: Python Dependencies (only rebuild when requirements.txt changes)
# ============================================
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ============================================
# LAYER 3: Playwright Browser (only rebuild when Playwright version changes)
# ============================================
RUN playwright install --with-deps chromium

# ============================================
# LAYER 4: Static Assets (rarely changes)
# ============================================
RUN mkdir -p static/js && \
    wget -O static/js/tailwindcss.js https://cdn.tailwindcss.com && \
    wget -O static/js/lucide.js https://unpkg.com/lucide@latest

# ============================================
# LAYER 5: Application Code (changes frequently - LAST for best caching)
# ============================================
COPY . /app
ENV PYTHONPATH=/

RUN mkdir -p /data

CMD ["python", "main.py"]
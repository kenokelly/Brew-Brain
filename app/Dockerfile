FROM python:3.11-slim-bookworm

WORKDIR /app

# ============================================
# LAYER 1: System Dependencies (Optimized for slim)
# ============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    libatlas-base-dev \
    libopenblas-dev \
    gfortran \
    libgpiod2 \
    wget \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# LAYER 2: Core Scientific Stack (Rarely changes)
# ============================================
COPY requirements-core.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install -r requirements-core.txt

# ============================================
# LAYER 3: Application Dependencies
# ============================================
COPY requirements-app.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-app.txt



# ============================================
# LAYER 4: Application Code
# ============================================
COPY . /app
ENV PYTHONPATH=/
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /data

CMD ["python", "main.py"]
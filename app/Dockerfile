FROM python:3.11-bookworm

WORKDIR /app

# Install system dependencies for Scipy/Numpy on ARM64
RUN apt-get update && apt-get install -y \
    libatlas-base-dev \
    gfortran \
    libgpiod2 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    flask \
    flask-cors \
    influxdb-client \
    pandas \
    numpy \
    scipy \
    requests

COPY brew_brain.py app.py
COPY static static

RUN mkdir /data

CMD ["python", "app.py"]
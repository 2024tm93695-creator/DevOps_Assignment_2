# Stage 1 – build / install dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2 – minimal runtime image
FROM python:3.12-slim

LABEL maintainer="ACEest Fitness & Gym DevOps Team"
LABEL version="3.2.4"
LABEL description="ACEest Fitness & Gym - Flask REST API"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app.py .

# Non-root user for security
RUN adduser --disabled-password --gecos "" aceest
USER aceest

ENV FLASK_APP=app.py
ENV FLASK_DEBUG=false
ENV PORT=5000

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]

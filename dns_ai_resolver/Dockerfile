# ---- Stage 1: Builder ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Install only needed packages into a temporary layer
RUN pip install --no-cache-dir dnslib requests python-dotenv

# ---- Stage 2: Final Runtime ----
FROM python:3.12-alpine

WORKDIR /app

# Copy only what's needed
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY dns_ai_resolver.py ./
COPY .env ./

# Expose UDP port
EXPOSE 5353/udp

ENTRYPOINT ["python", "dns_ai_resolver.py"]

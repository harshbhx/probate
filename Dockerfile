# The Courthouse (API, court, and the built website) as one image.
# The living family still runs on Fly Sprites; this image is for running the Courthouse anywhere
# else, such as a laptop, a VM or a judge's machine, in simulation or against real connectors.
#
#   docker build -t probate .
#   docker run -p 8080:8080 -v probate-data:/data probate
#
# Config is read from the environment (see services/core/.env.example). Nothing secret is baked in.

FROM node:22-slim AS web
WORKDIR /src
COPY package.json package-lock.json ./
COPY apps apps
COPY packages packages
RUN npm ci --ignore-scripts
RUN npm run build -w @probate/web

FROM python:3.13-slim
LABEL org.opencontainers.image.source="https://github.com/harshbhx/probate" \n      org.opencontainers.image.description="Probate Courthouse: the API, the court and the live family site. Starts in simulation mode, no keys needed." \n      org.opencontainers.image.licenses="MIT"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PROBATE_DATA_DIR=/data \
    PROBATE_WEB_DIST=/app/apps/web/dist \
    PROBATE_CONFIG_DIR=/app/config
WORKDIR /app
COPY services/core services/core
RUN pip install --no-cache-dir -e services/core
COPY config config
COPY --from=web /src/apps/web/dist apps/web/dist
RUN useradd --system --uid 10001 probate && mkdir /data && chown probate /data
USER probate
VOLUME /data
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8080/', timeout=4)" || exit 1
CMD ["python", "-m", "uvicorn", "probate.courthouse.app:app", "--host", "0.0.0.0", "--port", "8080"]

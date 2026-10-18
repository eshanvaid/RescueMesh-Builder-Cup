FROM node:22-bookworm-slim AS web
WORKDIR /build
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt
COPY server/rescuemesh /app/server/rescuemesh
COPY --from=web /build/dist /app/server/static
RUN useradd --create-home --uid 10001 rescuemesh
USER rescuemesh
ENV PYTHONPATH=/app/server RESCUEMESH_STORE=firestore
EXPOSE 8080
CMD ["sh","-c","exec uvicorn rescuemesh.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

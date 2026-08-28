FROM python:3.12-slim

WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir .

ENV CI_LOG_ROOT=/app
EXPOSE 8765

CMD ["python", "-m", "ci_log_mcp.server", "--transport", "http", "--host", "0.0.0.0", "--port", "8765"]

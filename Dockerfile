FROM python:3.11-slim

# System deps for lxml, Pillow, and PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxslt1.1 libjpeg62-turbo libwebp7 libtiff6 \
    libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .

# Copy application code and frontend
COPY src/ src/
COPY frontend/ frontend/
COPY AGENTS.md ./

# HF Spaces requires a non-root user
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/data /data \
    && chown -R appuser:appuser /app /data

USER appuser

# Pre-download PaddleOCR models at build time (avoids first-request delay)
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='fr', show_log=False)" 2>/dev/null || true

# Default storage root — overridden in Space mode via /data
ENV STORAGE_ROOT=/app/data
ENV HOST=0.0.0.0
ENV PORT=7860

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "7860"]

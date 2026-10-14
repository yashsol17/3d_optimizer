# 3D Asset Optimization Engine — FastAPI + headless Blender
# Built for Hugging Face Spaces (Docker SDK), but runs anywhere Docker does.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    BLENDER_SERIES=4.5 \
    BLENDER_VERSION=4.5.3 \
    BLENDER_PATH=/opt/blender/blender \
    STORAGE_DIR=/tmp/storage \
    HOME=/tmp \
    HOST=0.0.0.0 \
    PORT=7860

# Shared libraries Blender links against even with --background
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates xz-utils \
        libx11-6 libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 \
        libsm6 libice6 libgl1 libegl1 libglu1-mesa libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# Official Blender build — the distro package pulls in a desktop stack we don't need
RUN curl -fsSL "https://download.blender.org/release/Blender${BLENDER_SERIES}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
        -o /tmp/blender.tar.xz \
    && mkdir -p /opt/blender \
    && tar -xJf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 \
    && rm /tmp/blender.tar.xz \
    && "$BLENDER_PATH" --version

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY . .

# Spaces runs the container as uid 1000; storage lives in /tmp so it stays writable
RUN useradd -m -u 1000 app \
    && mkdir -p /tmp/storage/inputs /tmp/storage/outputs \
    && chown -R app:app /app /tmp/storage
USER app

EXPOSE 7860

CMD ["python", "backend/main.py"]

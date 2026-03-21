FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y \
    git \
    ffmpeg \
    wget \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better Docker layer caching)
COPY requirements.txt .

# 1) Upgrade pip
# 2) Install setuptools+wheel FIRST so pkg_resources is available
# 3) Install all project requirements
# 4) Force-reinstall setuptools so no later package can downgrade/remove it
RUN pip3 install --no-cache-dir --root-user-action=ignore -U pip && \
    pip3 install --no-cache-dir --root-user-action=ignore -U setuptools>=68.0.0 wheel && \
    pip3 install --no-cache-dir --root-user-action=ignore -r requirements.txt && \
    pip3 install --no-cache-dir --root-user-action=ignore --force-reinstall "setuptools>=68.0.0"

# Copy rest of the project
COPY . .

# Expose port for Render keep-alive health check
EXPOSE 10000

# Run the bot
CMD ["python3", "-m", "BeatVerseProbot"]

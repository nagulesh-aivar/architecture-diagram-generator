# Backend Dockerfile for Architecture Diagram Generator
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    graphviz \
    git \
    cmake \
    ninja-build \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv (provides uvx for diagram generation)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Verify uv and uvx are installed
RUN uvx --version && dot -V

# Copy requirements files
# COPY requirements.txt /app/root_requirements.txt
COPY Backend/requirements.txt /app/backend_requirements.txt

# Install Python dependencies
# Install root requirements first (basic packages)
# RUN pip3 install --no-cache-dir -r /app/root_requirements.txt

# Install backend requirements
# Note: strands-agents is in backend_requirements.txt
RUN pip3 install --no-cache-dir -r /app/backend_requirements.txt

# Copy backend code
COPY Backend/ /app/
COPY pdf_extractor.py /app/
# COPY diagram-generator.py /app/

# Create necessary directories
RUN mkdir -p /app/uploads /app/outputs /app/outputs/generated-diagrams

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Run the application
CMD ["python3", "main.py"]


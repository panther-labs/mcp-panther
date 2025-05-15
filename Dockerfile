# Build stage
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install curl and build dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

# Copy project files
COPY . .

# Install dependencies and build package
RUN uv pip install --system -e .

# Runtime stage
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variable to indicate Docker environment
ENV MCP_PANTHER_DOCKER_RUNTIME=true

# Copy only the installed packages and project files
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/mcp-panther /usr/local/bin/mcp-panther
COPY . .

# Command to run the server
CMD ["mcp-panther"] 
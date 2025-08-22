FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Create download directory
ENV DOWNLOAD_PATH=/data
RUN mkdir -p ${DOWNLOAD_PATH}

# Copy project metadata first (to install dependencies)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN pip install uv
RUN uv sync

# Copy source code
COPY src ./src

# Activate virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Start the MCP server
CMD ["python", "src/arxiv_server/server.py"]

FROM python:3.11-slim

WORKDIR /workspace

# Copy the dependency file
COPY pyproject.toml ./

# Install the dependencies (matching the previous working setup)
RUN pip install --no-cache-dir -e ".[dev]"

# Copy the rest of the application
COPY . .

# Force Uvicorn to bind to 0.0.0.0 and the dynamic PORT variable
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

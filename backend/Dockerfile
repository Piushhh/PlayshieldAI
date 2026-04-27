FROM python:3.11-slim

WORKDIR /app

# Install dependencies first to leverage Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Force Uvicorn to bind to 0.0.0.0 and the dynamic PORT variable
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}

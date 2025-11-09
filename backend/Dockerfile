# Use Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose port (usually 8000, 5000, or 8080)
EXPOSE 8000

# Start command - YE CHANGE KARNA TERI APP KE HISAB SE
CMD ["python", "app.py"]

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The app reads/writes ../data relative to backend/ — mount it as a volume
# in docker-compose so the SQLite file and knowledge base survive restarts.
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

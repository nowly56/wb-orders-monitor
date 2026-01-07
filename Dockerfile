FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

# Create empty orders.json if not exists
RUN echo "[]" > orders.json

CMD ["python", "bot.py"]

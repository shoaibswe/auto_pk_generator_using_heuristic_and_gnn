#Dockerfile

FROM python:3.10-slim

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.install
ENV PYTHONUNBUFFERED=1
CMD ["python", "main.py"]

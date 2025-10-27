# Use Python base
FROM python:3.14-slim
WORKDIR /usr/src/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV CONGRESS_LOG_DIR=/var/log/congress
RUN mkdir -p /var/log/congress /usr/src/app/bulk_data
EXPOSE 8000 8080
CMD ["python", "cbw_main.py", "--download", "--extract"]
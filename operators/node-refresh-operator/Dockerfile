FROM python:3.11-slim

WORKDIR /src

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY operator.py .

ENTRYPOINT ["kopf", "run", "--standalone", "/src/operator.py"]

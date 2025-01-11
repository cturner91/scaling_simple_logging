FROM python:3.12
WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y iputils-ping

RUN pip install --upgrade pip && pip install -r requirements.txt

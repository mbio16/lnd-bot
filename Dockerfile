FROM python:3.8-slim-buster

LABEL maintainer="mbio16"
LABEL version="1.0"

#RUN adduser -D pyuser

#USER pyuser

RUN apt-get update

WORKDIR /app

#COPY --chown=worker:worker . .

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt 

ADD ./src .
#RUN pip3 install  --user -r requirements.txt

CMD ["python3", "main.py"]


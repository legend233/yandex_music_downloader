FROM python:3.11.2-alpine3.17
LABEL yuchoba="yu@vtechnology.ru"
RUN apk update && apk upgrade && apk add git && apk add bash
RUN pip install --upgrade pip
RUN ["mkdir", "/music"]
RUN ["mkdir", "/books"]
ENV TELEGRAMM_TOKEN="telegramm_token"
ENV YA_TOKEN="ya_token"
ENV DOWNLOAD_PATH_MUSIC="/music"
ENV DOWNLOAD_PATH_BOOKS="/books"
WORKDIR /app
COPY ./API.py .
COPY ./tbot.py .
COPY ./requirements.txt .
RUN pip install -r requirements.txt

CMD ["python3", "./tbot.py"]
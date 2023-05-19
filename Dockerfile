FROM python:3.11.2-alpine3.17
LABEL yuchoba="yu@vtechnology.ru"
RUN apk update && apk upgrade && apk add git && apk add bash
RUN pip install --upgrade pip && pip install pyTelegramBotAPI && pip install music-tag && pip install python-dotenv && pip install loguru
RUN pip install git+https://github.com/MarshalX/yandex-music-api/@dev
RUN ["mkdir", "/download"]
RUN ["mkdir", "/books"]
ENV TELEGRAMM_TOKEN="telegramm_token"
ENV YA_TOKEN="ya_token"
ENV DOWNLOAD_PATH="/download"
ENV DOWNLOAD_PATH_BOOKS="/books"
WORKDIR /app
COPY ./API.py .
COPY ./tbot.py .

CMD ["python3", "./tbot.py"]
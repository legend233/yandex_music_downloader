FROM python:3.11.2-alpine3.17
LABEL yuchoba="yu@vtechnology.ru"
RUN apk update && apk upgrade && apk add bash
RUN pip install --upgrade pip && pip install yandex-music && pip install pyTelegramBotAPI && pip install music-tag && pip install python-dotenv
RUN ["mkdir", "/download"]
ENV TELEGRAMM_TOKEN="telegramm_token"
ENV YA_TOKEN="ya_token"
ENV DOWNLOAD_PATH="download"
WORKDIR /app
COPY ./API.py .
COPY ./tbot.py .

CMD ["python3", "./tbot.py"]
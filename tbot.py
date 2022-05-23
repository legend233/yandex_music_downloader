#!/usr/bin/python3
# -*- coding: utf-8 -*-

import telebot
from mainv2 import download_artist, download_album, quantity_albums, quantity_track
import re
from config import telegramm_token

bot = telebot.TeleBot(telegramm_token)

print("я работаю. Буду висеть тут пока не остановишь или не крашнусь")


@bot.message_handler(commands=["start"])

def start(message):
    bot.send_message(message.chat.id, "Привет! Я могу скачать твою любимую музыку! Выполни команду скачать и Отправь мне ссылку с яндекс музыки.", parse_mode="html")

@bot.message_handler(commands=["d_artist"])
def download(message):
    bot.send_message(
        message.chat.id,
        "Сейчас мы скачаем всю музыку указанного артиста. отправь мне ссылку на яндекс музыку: ",
        parse_mode="html")
    @bot.message_handler()
    def artist_link(message):
        download_link = message.text
        artist_id = re.split('\?|!|,|-|]', download_link.split("artist/")[1])[0]
        try:
            bot.send_message(message.chat.id, f"Уже качаю, всего альбомов {len(quantity_albums(artist_id))}", parse_mode="html")
            download_artist(download_link)
            bot.send_message(message.chat.id, f"Все альбомы артиста с ID:{artist_id} скачены", parse_mode="html")
        except:
            bot.send_message(message.chat.id, f"Что-то пошло не так. В {download_link} не удалось найти artist ID", parse_mode="html")

@bot.message_handler(commands=["d_album"])
def download(message):
    bot.send_message(
        message.chat.id,
        "Сейчас мы скачаем все песни из указанного альбома. отправь мне ссылку на яндекс музыку: ",
        parse_mode="html")
    @bot.message_handler()
    def album_link(message):
        download_link = message.text
        album_id = re.split('\?|!|,|-|]', download_link.split("album/")[1])[0]
        try:
            bot.send_message(message.chat.id, f"Уже качаю, всего песен в альбоме {quantity_track(album_id)}", parse_mode="html")
            download_album(album_id)
            bot.send_message(message.chat.id, f"Все песни из указанного альбома с ID:{album_id} скачены", parse_mode="html")
        except:
            bot.send_message(message.chat.id, f"Что-то пошло не так. В {download_link} не удалось найти album ID", parse_mode="html")


bot.polling(none_stop=True)



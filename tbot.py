#!/usr/bin/python3
# -*- coding: utf-8 -*-

import telebot
from mainv2 import main, quantity
import re
from config import telegramm_token

bot = telebot.TeleBot(telegramm_token)

print("я работаю. Буду висеть тут пока не остановишь или не крашнусь")


@bot.message_handler(commands=["start"])

def start(message):
    bot.send_message(message.chat.id, "Привет! Я могу скачать твою любимую музыку! Выполни команду скачать и Отправь мне ссылку с яндекс музыки.", parse_mode="html")

@bot.message_handler(commands=["download"])
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
            bot.send_message(message.chat.id, f"Уже качаю, всего альбомов {len(quantity(artist_id))}", parse_mode="html")
            main(download_link)
            bot.send_message(message.chat.id, f"Все альбомы артиста с ID:{artist_id} скачены", parse_mode="html")
        except:
            bot.send_message(message.chat.id, f"Что-то пошло не так. В {download_link} не удалось найти artist ID", parse_mode="html")


bot.polling(none_stop=True)



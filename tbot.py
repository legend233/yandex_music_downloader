#!/usr/bin/python3
# -*- coding: utf-8 -*-

import telebot
import os
from telebot import types
from API import (
    send_search_request_and_print_result, 
    search_and_download_artist, 
    download_album, 
    get_album_info, 
    download_path, 
    download_book, 
    get_book_info,
    folder_audiobooks,
)

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

bot = telebot.TeleBot(os.getenv('TELEGRAMM_TOKEN_TEST'))


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Привет, хочешь скачать музыку или аудиокниги? /download')


@bot.message_handler(commands=['download'])
def download_command(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    item1 = types.KeyboardButton("Артиста")
    item2 = types.KeyboardButton("Альбом")
    item3 = types.KeyboardButton('Книгу')
    markup.add(item1, item2, item3)
    msg = bot.send_message(message.chat.id, 'Что будем качать?', reply_markup=markup)
    bot.register_next_step_handler(msg, take_you_choise)


def take_you_choise(message):
    if message.text == "Артиста":
        msg = bot.send_message(message.chat.id, 'Напиши название артиста или группы')
        bot.register_next_step_handler(msg, input_data_artist)
    elif message.text == "Альбом":
        msg = bot.send_message(message.chat.id, 'скинь ссылку на альбом')
        bot.register_next_step_handler(msg, input_data_albom)
    elif message.text == "Книгу":
        msg = bot.send_message(message.chat.id, 'Кинь мне ссылку на книгу с яндекс-музыки')
        bot.register_next_step_handler(msg, input_data_book)


def input_data_artist(message):
    try:
        artist = send_search_request_and_print_result(message.text)
        bot.send_message(message.chat.id, artist)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        item1 = types.KeyboardButton("Качаем!")
        item2 = types.KeyboardButton("Отмена")
        markup.add(item1, item2)
        msg = bot.send_message(message.chat.id, 'Качаем музыку этого артиста?', reply_markup=markup)
        artist_result = artist[artist.find('>>>') + 3:artist.rfind('<<<')].lower()
        cont_type = 'Artist'
        bot.register_next_step_handler(msg, download_from_input_data, cont_type, artist_result)
    except:
        bot.send_message(message.chat.id, f'Что-то пошло не так при поиске информации о артисте {artist}. Посмотри логи.')
        with open(f'{download_path}/log.log', 'rb') as file:
            bot.send_document(message.chat.id, file)

def input_data_albom(message):
    try:
        album_id = ''.join([x for x in message.text if x.isdigit()])
        print('Album_id: ', album_id)
        album_mess = get_album_info(album_id=album_id)
        bot.send_message(message.chat.id, album_mess)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        item1 = types.KeyboardButton("Качаем!")
        item2 = types.KeyboardButton("Отмена")
        markup.add(item1, item2)
        msg = bot.send_message(message.chat.id, 'Качаем этот альбом?', reply_markup=markup)
        cont_type = 'Album'
        bot.register_next_step_handler(msg, download_from_input_data, cont_type, album_id)
    except:
        bot.send_message(message.chat.id, 'Что-то пошло не так при поиске информации о альбоме. Посмотри логи.')
        with open(f'{download_path}/log.log', 'rb') as file:
            bot.send_document(message.chat.id, file)


def input_data_book(message):
    try:
        book_id = ''.join([x for x in message.text if x.isdigit()])
        print('Book_id: ', book_id)
        book_mess = get_book_info(album_id=book_id)
        bot.send_message(message.chat.id, book_mess)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        item1 = types.KeyboardButton("Качаем!")
        item2 = types.KeyboardButton("Отмена")
        markup.add(item1, item2)
        msg = bot.send_message(message.chat.id, 'Качаем эту аудиокнигу?', reply_markup=markup)
        cont_type = 'Book'
        bot.register_next_step_handler(msg, download_from_input_data, cont_type, book_id)
    except:
        bot.send_message(message.chat.id, 'Что-то пошло не так при поиске информации о аудиокниге. Посмотри логи.')
        with open(f'{download_path}/log.log', 'rb') as file:
            bot.send_document(message.chat.id, file)


def download_from_input_data(message, *args):
    try:
        if message.text == 'Качаем!' and args[0] == 'Artist':
            d_artist = search_and_download_artist(args[1])
            bot.send_message(message.chat.id, d_artist)
        elif message.text == 'Качаем!' and args[0] == 'Album':
            d_album = download_album(args[1])
            bot.send_message(message.chat.id, d_album)
        elif message.text == 'Качаем!' and args[0] == 'Book':
            d_book = download_book(args[1])
            bot.send_message(message.chat.id, d_book)
    except:
        bot.send_message(message.chat.id, "Что-то пошло не так при скачивании. Посмотри консоль")
        with open(f'{download_path}/log.log', 'rb') as file:
            bot.send_document(message.chat.id, file)

bot.polling(none_stop=True)



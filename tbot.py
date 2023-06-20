#!/usr/bin/python3
# -*- coding: utf-8 -*-
import time
import telebot
import os
from telebot import types
from API import (
    send_search_request_and_print_result,
    search_and_download_artist,
    download_album,
    get_album_info,
    folder_music,
    download_book,
    get_book_info,
    folder_audiobooks,
    get_podcast_info,
    download_podcast,
    folder_podcasts
)
from dotenv import load_dotenv, find_dotenv
import threading
from loguru import logger
import shutil

cur_dir = folder_music
root_dir = folder_music
load_dotenv(find_dotenv())
bot = telebot.TeleBot(os.getenv('TELEGRAMM_TOKEN'))
download_queue = list()

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Привет, хочешь скачать музыку, аудиокниги, подкасты? /download')



@bot.message_handler(commands=['download'])
def download_command(message):
    """
    Обрабатывает команду 'download' для бота. Отображает клавиатуру ответа с вариантами
    для выбора типа медиафайла для загрузки. 

    Аргументы:
    - message: объект сообщения, представляющий сообщение, отправленное пользователем.

    Возвращает:
    - None
    """
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    item1 = types.KeyboardButton("Артиста")
    item2 = types.KeyboardButton("Альбом")
    item3 = types.KeyboardButton('Книгу')
    item4 = types.KeyboardButton('Подкаст')
    markup.add(item1, item2, item3, item4)
    msg = bot.send_message(message.chat.id, 'Что будем качать?', reply_markup=markup)
    bot.register_next_step_handler(msg, take_you_choise)


def take_you_choise(message):
    """Эта функция обрабатывает сообщение, запрашивает у пользователя дополнительную информацию в зависимости от текста сообщения и регистрирует обработчик следующего шага."""
    if message.text == "Артиста":
        msg = bot.send_message(message.chat.id, 'Напиши название артиста или группы')
        bot.register_next_step_handler(msg, input_data_artist)
    elif message.text == "Альбом":
        msg = bot.send_message(message.chat.id, 'скинь ссылку на альбом')
        bot.register_next_step_handler(msg, input_data_albom)
    elif message.text == "Книгу":
        msg = bot.send_message(message.chat.id, 'Кинь мне ссылку на книгу с яндекс-музыки')
        bot.register_next_step_handler(msg, input_data_book)
    elif message.text == "Подкаст":
        msg = bot.send_message(message.chat.id, 'Кинь мне ссылку на подкаст с яндекс-музыки')
        bot.register_next_step_handler(msg, input_data_podcast)


def input_data_artist(message):
    """
    Обрабатывает сообщение, запрашивает у пользователя информацию о артисте.
    """
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
        with open(f'{folder_music}/log.log', 'rb') as file:
            bot.send_document(message.chat.id, file)

def input_data_albom(message):
    """Обрабатывает сообщение, запрашивает у пользователя информацию о альбоме."""
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
        with open(f'{folder_music}/log.log', 'rb') as file:
            bot.send_document(message.chat.id, file)


def input_data_book(message):
    """Обрабатывает сообщение, запрашивает у пользователя информацию о аудиокниге."""
    try:
        book_id = ''.join([x for x in message.text if x.isdigit()])
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
        with open(f'{folder_music}/log.log', 'rb') as file:
            bot.send_document(message.chat.id, file)


def input_data_podcast(message):
    """Обрабатывает сообщение, запрашивает у пользователя информацию о подкасте."""
    try:
        podcast_id = ''.join([x for x in message.text if x.isdigit()])
        podcast_mess = get_podcast_info(podcast_id=podcast_id)
        bot.send_message(message.chat.id, podcast_mess)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        item1 = types.KeyboardButton("Качаем!")
        item2 = types.KeyboardButton("Отмена")
        markup.add(item1, item2)
        msg = bot.send_message(message.chat.id, 'Качаем этот подкаст?', reply_markup=markup)
        cont_type = 'Podcast'
        bot.register_next_step_handler(msg, download_from_input_data, cont_type, podcast_id)
    except:
        bot.send_message(message.chat.id, 'Что-то пошло не так при поиске информации о подкасте. Посмотри логи.')
        with open(f'{folder_music}/log.log', 'rb') as file:
            bot.send_document(message.chat.id, file)


def download_from_input_data(message, *args):
    """Добавляет закачку в очередь."""
    try:
        if message.text == 'Качаем!':
            if args[0] == 'Artist':
                download_queue.append((search_and_download_artist, args[1], message.chat.id))
            elif args[0] == 'Album':
                download_queue.append((download_album, args[1], message.chat.id))
            elif args[0] == 'Book':
                download_queue.append((download_book, args[1], message.chat.id))
            elif args[0] == 'Podcast':
                download_queue.append((download_podcast, args[1], message.chat.id))
            bot.send_message(message.chat.id, f"Добавил закачку в очередь.\nВсего в очереди: {len(download_queue)} задачи")
        else:
            bot.send_message(message.chat.id, f"Не хочешь? Можешь скачать что-то другое.")
    except:
        bot.send_message(message.chat.id, "Что-то пошло не так при добавлении в очередь. Посмотри log")
        with open(f'{folder_music}/log.log', 'rb') as file:
            bot.send_document(message.chat.id, file)


def download_monitor():
    """Основной цикл скачивания."""
    while True:
        time.sleep(10)
        if download_queue != []:
            data = download_queue[0]
            try:
                result = data[0](data[1])
                bot.send_message(chat_id=data[2], text=result)
            except:
                bot.send_message(chat_id=data[2], text=f"Что-то пошло не так при скачивании ID:{data[1]}. Посмотри log")
            download_queue.pop(0)
            bot.send_message(data[2], f"Всего осталось в очереди: {len(download_queue)} задачи")


@bot.message_handler(commands=['files'])
def what_files(message):
    markup = types.InlineKeyboardMarkup()
    item1 = types.InlineKeyboardButton(text='Музыка', callback_data='files_music')
    item2 = types.InlineKeyboardButton(text='Аудиокнига', callback_data='files_book')
    item3 = types.InlineKeyboardButton(text='Подкаст', callback_data='files_podcast')
    markup.add(item1, item2, item3)
    msg = bot.send_message(message.chat.id, 'Какие файлы тебе нужны?', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    global cur_dir
    global root_dir
    global dir_ls
    global files_ls
    
    def callmenu():
        dir_ls = [folder for folder in os.listdir(cur_dir) if os.path.isdir(cur_dir+'/'+folder)]
        files_ls = [filee for filee in os.listdir(cur_dir) if os.path.isfile(cur_dir+'/'+filee)]
        mess = os.path.abspath(cur_dir).replace(os.path.abspath(root_dir), '') 
        markup = types.InlineKeyboardMarkup()
        dirs_buttons = [types.InlineKeyboardButton(text='📁 '+folder, callback_data=folder) for folder in dir_ls]
        files_buttons = [types.InlineKeyboardButton(text='💾 '+filee, callback_data=filee) for filee in files_ls]
        back_button = types.InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='Back')
        exit_button = types.InlineKeyboardButton(text='❌ ВЫХОД', callback_data='Exit')
        download_button = types.InlineKeyboardButton(text='⬇️ Скачать все!', callback_data='Download')
        markup.add(download_button, back_button, exit_button, *dirs_buttons, *files_buttons)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='/'+mess, reply_markup=markup)

    if call.data == 'files_music':
        cur_dir = folder_music
        root_dir = folder_music
        callmenu()
    elif call.data == "files_book":
        cur_dir = folder_audiobooks
        root_dir = folder_audiobooks
        callmenu()
    elif call.data == "files_podcast":
        cur_dir = folder_podcasts
        root_dir = folder_podcasts
        callmenu()

    elif call.data == 'Download':
        if os.path.abspath(cur_dir) != os.path.abspath(root_dir):
            send_temp_file = root_dir + '/' + cur_dir[cur_dir.rfind('/'):]
            shutil.make_archive(send_temp_file, 'zip', cur_dir)
            try:
                with open(f'{send_temp_file}.zip', 'rb') as file:
                    bot.send_document(call.message.chat.id, file)
            except telebot.apihelper.ApiTelegramException:
                bot.send_message(call.message.chat.id, "сработало ограничение в 50 мб")
            finally:
                os.remove(path=f'{send_temp_file}.zip')
        else:
            bot.send_message(call.message.chat.id, "Нельзя качать в корневом каталоге!", reply_markup=None)
    elif call.data == 'Back':
        if os.path.abspath(cur_dir) != os.path.abspath(root_dir):
            cur_dir = os.path.join(cur_dir, '..')
        else:
            bot.send_message(call.message.chat.id, "Ты в корневом каталоге! Выше нельзя", reply_markup=None)
        callmenu()
    elif call.data == 'Exit':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, "Не хочешь... Как хочешь!", reply_markup=None)
    elif call.data in [folder for folder in os.listdir(cur_dir) if os.path.isdir(cur_dir+'/'+folder)]:
        cur_dir = os.path.join(cur_dir, call.data)
        callmenu()
    elif call.data in [filee for filee in os.listdir(cur_dir) if os.path.isfile(cur_dir+'/'+filee)]:
        send_file = cur_dir + '/' + call.data
        try:
            with open(f'{send_file}', 'rb') as file:
                bot.send_document(call.message.chat.id, file)
        except telebot.apihelper.ApiTelegramException:
            bot.send_message(call.message.chat.id, "сработало ограничение в 50 мб")


@logger.catch
def echo_status(downloader_status, bot_status):
    while True:
        
        if not downloader_status or not bot_status:
            mess = f"Внимание!!!\nСтатус потока скачивания: {downloader_status.is_alive()}\nСтатус потока бота: {bot_status.is_alive()}"
            logger.info(mess)
            time.sleep(600)
        else:
            mess = f"\nСтатус потока скачивания: {downloader_status.is_alive()}\nСтатус потока бота: {bot_status.is_alive()}"
            logger.info(mess)
            time.sleep(3600)


if __name__ == '__main__':
    download_monitor_thread = threading.Thread(target=download_monitor)
    download_monitor_thread.start() # запуск потока скачивания медиафайлов
    bot_thread = threading.Thread(target=bot.polling, kwargs={'none_stop': True})
    bot_thread.start() # запуск бота в отдельном потоке
    
    echo_status_thread = threading.Thread(target=echo_status, kwargs={
        'downloader_status': download_monitor_thread,
        'bot_status': bot_thread})
    echo_status_thread.start()
    

#!/usr/bin/python3
# -*- coding: utf-8 -*-
import time
import telebot
import os
from telebot import types, apihelper
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

start_window = 0
cur_dir = folder_music
root_dir = folder_music
dir_ls = []
files_ls = []
load_dotenv(find_dotenv())
# Настройка прокси для Telegram API (опционально).
# Если TELEGRAM_PROXY_URL не задан (пусто) — бот работает напрямую.
# Формат: socks5://user:pass@host:port
proxy_url = os.getenv('TELEGRAM_PROXY_URL')
if proxy_url:
    apihelper.proxy = {'https': proxy_url}
bot = telebot.TeleBot(os.getenv('TELEGRAMM_TOKEN'))
download_queue = list()


@bot.message_handler(commands=['start'])
def start_message(message):
    mess = "Привет, хочешь скачать музыку, аудиокниги, подкасты? /download\
        \nХочешь посмотреть скаченное? /files"
    bot.send_message(message.chat.id, mess)



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
    start_window = 0
    markup = types.InlineKeyboardMarkup()
    item1 = types.InlineKeyboardButton(text='Музыка', callback_data='files_music')
    item2 = types.InlineKeyboardButton(text='Аудиокнига', callback_data='files_book')
    item3 = types.InlineKeyboardButton(text='Подкаст', callback_data='files_podcast')
    markup.add(item1, item2, item3)
    msg = bot.send_message(message.chat.id, 'Какие файлы тебе нужны?', reply_markup=markup)
    logger.info(f"Пользователь {message.chat.id} открыл инлайн меню просмотра файлов")


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    """обработчик команды files. Отображает файловый менеджер с возможностью скачивать."""
    global cur_dir
    global root_dir
    global dir_ls
    global files_ls
    global start_window
    block_send_status = False
    if call.data == 'Exit':
        block_send_status = True
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(call.message.chat.id, "Не хочешь... Как хочешь!", reply_markup=None)
        logger.info(f"Пользователь {call.message.chat.id} закрыл инлайн меню просмотра файлов")
    elif call.data == 'DownloadFolder':
        block_send_status = True
        if os.path.abspath(cur_dir) != os.path.abspath(root_dir):
            send_temp_file = root_dir + cur_dir[cur_dir.rfind('/'):]
            shutil.make_archive(send_temp_file, 'zip', cur_dir)
            try:
                with open(f'{send_temp_file}.zip', 'rb') as f:
                    bot.send_document(call.message.chat.id, f)
                logger.info(f"Пользователь {call.message.chat.id} скачал архив с содержимим каталога {cur_dir}")
            except telebot.apihelper.ApiTelegramException:
                bot.send_message(call.message.chat.id, "сработало ограничение в 50 мб")
                logger.info(f"Пользователь {call.message.chat.id} не смог скачать архив с содержимим каталога {cur_dir}. Сработало ограничение в 50 мб")
            finally:
                os.remove(path=f'{send_temp_file}.zip')
        else:
            bot.send_message(call.message.chat.id, "Нельзя качать в корневом каталоге!", reply_markup=None)

    else:
        if call.data == 'files_music':
            cur_dir = folder_music
            root_dir = folder_music
            
        elif call.data == "files_book":
            cur_dir = folder_audiobooks
            root_dir = folder_audiobooks
            
        elif call.data == "files_podcast":
            cur_dir = folder_podcasts
            root_dir = folder_podcasts

        elif call.data == 'Back':
            start_window = 0
            if os.path.abspath(cur_dir) != os.path.abspath(root_dir):
                cur_dir = os.path.join(cur_dir, '..')
            else:
                bot.send_message(call.message.chat.id, "Ты в корневом каталоге! Выше нельзя", reply_markup=None)
        
        elif call.data == 'PrevP':
            start_window -= 15
            if start_window < 0:
                start_window = 0
        elif call.data == 'NextP':
            if start_window + 15 < len(dir_ls + files_ls):
                start_window += 15
            else:
                bot.send_message(call.message.chat.id, "Нет больше файлов", reply_markup=None)

        elif call.data in [''.join([y for y in x if y.isalnum()])[:15] for x in dir_ls]:
            for _ in dir_ls:
                if call.data == ''.join([y for y in _ if y.isalnum()])[:15]:
                    cur_dir = os.path.join(cur_dir, _)
            start_window = 0

        elif call.data in [''.join([y for y in x if y.isalnum()])[:15] for x in files_ls]:
            block_send_status = True
            for _ in files_ls:
                if call.data == ''.join([y for y in _ if y.isalnum()])[:15]:
                    send_file = cur_dir + '/' + _
                    print(send_file)

            try:
                with open(f'{send_file}', 'rb') as f:
                    bot.send_document(call.message.chat.id, f)
                logger.info(f"File {send_file} sended!!!")
            except telebot.apihelper.ApiTelegramException:
                bot.send_message(call.message.chat.id, "сработало ограничение в 50 мб")
                logger.error(f"сработало ограничение в 50 мб: {send_file} > 50 мб")

    if not block_send_status:
        dir_ls = sorted([folder for folder in os.listdir(cur_dir) if os.path.isdir(cur_dir+'/'+folder)])
        files_ls = sorted([filee for filee in os.listdir(cur_dir) if os.path.isfile(cur_dir+'/'+filee)])
        mess = os.path.abspath(cur_dir).replace(os.path.abspath(root_dir), '') 
        markup = types.InlineKeyboardMarkup()
        dirs_buttons = [types.InlineKeyboardButton(text='📁 '+folder, callback_data=''.join([x for x in folder if x.isalnum()])[:15]) for folder in dir_ls]
        files_buttons = [types.InlineKeyboardButton(text='💾 '+filee, callback_data=''.join([x for x in filee if x.isalnum()])[:15]) for filee in files_ls]
        item_inwindow_buttons = (dirs_buttons + files_buttons)[start_window:start_window+15]
    
        back_button = types.InlineKeyboardButton(text='⬅️ НАЗАД', callback_data='Back')
        exit_button = types.InlineKeyboardButton(text='❌ ВЫХОД', callback_data='Exit')
        download_button = types.InlineKeyboardButton(text='📲 Скачать все!', callback_data='DownloadFolder')
        
        prev_page_button = types.InlineKeyboardButton(text='◀️ Пред.стр.', callback_data='PrevP')
        next_page_button = types.InlineKeyboardButton(text='▶️ След.стр.', callback_data='NextP')
        
        markup.add(download_button, back_button, exit_button, *item_inwindow_buttons)
        if len(dirs_buttons + files_buttons) > 15:
            markup.add(prev_page_button, next_page_button)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='/'+mess, reply_markup=markup)
    elif block_send_status:
        block_send_status = False
@logger.catch
def echo_status(downloader_status, bot_status):
    while True:
        if not downloader_status or not bot_status:
            mess = f"Внимание!!!\nСтатус потока скачивания: {downloader_status.is_alive()}\nСтатус потока бота: {bot_status.is_alive()}"
            logger.error(mess)
            time.sleep(600)
            bot_thread.start()
        else:
            mess = f"\nСтатус потока скачивания: {downloader_status.is_alive()}\nСтатус потока бота: {bot_status.is_alive()}"
            logger.info(mess)
            time.sleep(3600)


if __name__ == '__main__':
    download_monitor_thread = threading.Thread(target=download_monitor)
    download_monitor_thread.start() # запуск потока скачивания медиафайлов
    bot_thread = threading.Thread(target=bot.infinity_polling, kwargs={'skip_pending':True})
    bot_thread.start() # запуск бота в отдельном потоке
    echo_status_thread = threading.Thread(target=echo_status, kwargs={
        'downloader_status': download_monitor_thread,
        'bot_status': bot_thread})
    echo_status_thread.start()
    

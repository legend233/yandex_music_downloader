import telebot
from telebot import types
import random
from API import send_search_request_and_print_result, search_and_download_artist

bot = telebot.TeleBot("5357988248:AAH2gueWZqk_up7KBMn4kaBWA5M1cMpA8Ng")


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Привет, хочешь скачать музыку себе на plex?')
@bot.message_handler(commands=['download'])
def download_command(message):
    markup=types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    item1=types.KeyboardButton("Артиста")
    item2 = types.KeyboardButton("Альбом")
    item3 = types.KeyboardButton('По ссылке')
    markup.add(item1, item2, item3)
    msg = bot.send_message(message.chat.id, 'Какую музыку будем качать?', reply_markup=markup)
    bot.register_next_step_handler(msg, take_you_choise)

def take_you_choise(message):
    if message.text == "Артиста":
        msg = bot.send_message(message.chat.id, 'Напиши название артиста или группы')
        bot.register_next_step_handler(msg, input_data_artist)
    elif message.text == "Альбом":
        msg = bot.send_message(message.chat.id, 'Напиши название альбома')
        bot.register_next_step_handler(msg, input_data_albom)
    elif message.text == "По ссылке":
        msg = bot.send_message(message.chat.id, 'Кинь мне ссылку на альбом или артиста с яндекс музыки')
        bot.register_next_step_handler(msg, input_data_link)


def input_data_artist(message):
    artist = send_search_request_and_print_result(message.text)
    bot.send_message(message.chat.id, artist)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    item1 = types.KeyboardButton("Качаем!")
    item2 = types.KeyboardButton("Отмена")
    markup.add(item1, item2)
    msg = bot.send_message(message.chat.id, 'Качаем музыку этого артиста?', reply_markup=markup)
    artist_result = artist[artist.find('>>>')+3:artist.rfind('<<<')].lower()
    bot.register_next_step_handler(msg, download_from_input_data, artist_result)

def input_data_albom(message):
    #artist = send_search_request_and_print_result(message.text)
    #bot.send_message(message.chat.id, artist)
    #markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    #item1 = types.KeyboardButton("Качаем!")
    #item2 = types.KeyboardButton("Отмена")
    #markup.add(item1, item2)
    #msg = bot.send_message(message.chat.id, 'Качаем музыку этого артиста?', reply_markup=markup)
    #artist_result = artist[artist.find('>>>')+3:artist.rfind('<<<')].lower()
    #bot.register_next_step_handler(msg, download_from_input_data, artist_result)
    pass


def input_data_link(message):
    #artist = send_search_request_and_print_result(message.text)
    #bot.send_message(message.chat.id, artist)
    #markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    #item1 = types.KeyboardButton("Качаем!")
    #item2 = types.KeyboardButton("Отмена")
    #markup.add(item1, item2)
    #msg = bot.send_message(message.chat.id, 'Качаем музыку этого артиста?', reply_markup=markup)
    #artist_result = artist[artist.find('>>>')+3:artist.rfind('<<<')].lower()
    #bot.register_next_step_handler(msg, download_from_input_data, artist_result)
    pass

def download_from_input_data(message, artist_result):
    if message.text == 'Качаем!':
        d_artist = search_and_download_artist(artist_result)
        bot.send_message(message.chat.id, d_artist)


        #Todo вызов функции скачать
'''
@bot.message_handler(content_types='text')
def message_reply(message):
    if message.text == "Артиста":
        bot.send_message(message.chat.id, 'Напиши название артиста или группы')
@bot.message_handler(content_types='text')
def message_reply(message):
    bot.send_message(message.chat.id,send_search_request_and_print_result(message))
    global valid_search
    valid_search= message
    markup=types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    item1 = types.KeyboardButton("Качаем!")
    item2 = types.KeyboardButton("Нет я попробую еще раз")
    markup.add(item1, item2)
    bot.send_message(message.chat.id, 'Качаем?', reply_markup=markup)

@bot.message_handler(content_types='text')
def message_reply(message):
    if message.text == "Качаем!":
        bot.send_message(message.chat.id, 'Сейчас скачаю, подожди')
        search_and_download_artist(valid_search)
        bot.send_message(message.chat.id, 'Готово!')
'''


bot.polling(none_stop=True)
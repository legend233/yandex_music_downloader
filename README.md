# Yandex music downloader
### Основано на:
#### * [MarshalX/yandex-music-api](https://github.com/MarshalX/yandex-music-api)
#### * [Telegram Bot API](https://github.com/eternnoir/pyTelegramBotAPI)
#### * [music-tag](https://github.com/KristoforMaynard/music-tag)

Программа для скачивания через интерфейс телеграмм бота всей музыки артиста (по названию), альбома (по share ссылке), плейлиста (по share ссылке), сборника (по share ссылке), аудиокниги (по share ссылке), подкаст канала (по share ссылке) с вашего аккаунта на yandex.music.ru. Рекомендуется для работы в паре с медиосервером музыки (например plex) и аудиокниг/подкастов (например audiobookshelf).

Для работы необходимо:
1. [Токен вашего яндекс аккаунта](https://github.com/MarshalX/yandex-music-api/discussions/513#discussioncomment-2729781)
2. [Токен телеграмм вашего бота](https://lifehacker.ru/kak-sozdat-bota-v-telegram/)

# Установка
## Linux / MacOS / Windows
    1. запустить git bush // для Windows
    1. запустить терминал // для Linux/MacOS
    2. git clone 'THIS_PROJECT'
    3. cd yandex_music_downloader
    4. pip install -r requirements.txt
    5. nano .env
______________ 
#### .env

    TELEGRAMM_TOKEN=YOUR_TOKEN
    YA_TOKEN=YOUR_TOKEN
    DOWNLOAD_PATH_MUSIC=YOUR_DOWNLOAD_PATH
    DOWNLOAD_PATH_BOOKS=YOUR_DOWNLOAD_PATH
    DOWNLOAD_PATH_PODCASTS=YOUR_DOWNLOAD_PATH
______________

    6. python tbot.py

## Docker
[yuchoba/ya-download](https://hub.docker.com/r/yuchoba/ya-download)
# Использование
1. Отправьте команду вашему телеграм боту:

    /start - обзор существующих команд
    /download - скачать музыку, книгу, подкаст с яндекс музыки
    /files - просмотреть скаченное и получить в сообщении через телеграм


2. Выберете один из вариантов скачивания, следуйте советом вашего бота.
3. Музыка скачивается в выбранную вами директорию "YOUR_DOWNLOAD_PATH"

Музыка, аудиокнига, подкасты скачиваются в максимальном доступном качестве до 320 kbps с записанными тегами, обложкой, текстом песни (в тег и в одноименный файла.txt), описанием книги, выпуска, если есть на яндексе.


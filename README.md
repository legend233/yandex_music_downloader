# yandex_music_downloader
### Основано на:
#### * MarshalX/yandex-music-api https://github.com/MarshalX/yandex-music-api
#### * Telegram Bot API https://github.com/eternnoir/pyTelegramBotAPI
#### * music-tag https://github.com/KristoforMaynard/music-tag

Телеграм бот + скачивание всей музыки артиста (по названию), альбома (по share ссылке), плейлиста (по share ссылке), сборника (по share ссылке) с вашего аккаунта на yandex.music.ru. Рекомендуется для работы в паре с медиосервером.
для работы необходимо:
1. Токен вашего яндекс аккаунта (https://github.com/MarshalX/yandex-music-api/)
2. Токен телеграмм вашего бота (https://lifehacker.ru/kak-sozdat-bota-v-telegram/)
3. config.py с вашими настройками в папке с программой

# Установка
## Linux / MacOS
    1. pip install python-dotenv music-tag pyTelegramBotAPI yandex-music --upgrade
    2. git clone 'THIS_PROJECT'
    3. cd yandex_music_downloader
    4. nano .env
______________ 
#### .env

    telegramm_token = "YOUR_TOKEN"
    ya_token = "YOUR_TOKEN"
    download_path = 'YOUR_DOWNLOAD_PATH'
______________

    5. python tbot.py

## Windows
    1. запустить git bush
    2. git clone 'THIS_PROJECT'
    3. cd yandex_music_downloader
    4. nano .env
______________ 
#### .env

    telegramm_token = "YOUR_TOKEN"
    ya_token = "YOUR_TOKEN"
    download_path = 'YOUR_DOWNLOAD_PATH'
______________
    5. pip install python-dotenv music-tag pyTelegramBotAPI yandex-music --upgrade
    6. python tbot.py

## Docker
https://hub.docker.com/r/yuchoba/ya-download
# Использование
1. Отправьте команду вашему телеграм боту:


    /download

2. Выберете один из вариантов скачивания, следуйте советом вашего бота.
3. Музыка скачивается в выбранную вами директорию "YOUR_DOWNLOAD_PATH"

Музыка качаются в максимальном доступном качестве до 320 kbps с записанными тегами, обложкой, текстом песни (в тег и в одноименный файла.txt), если он есть на яндексе.


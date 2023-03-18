# yandex_music_downloader
Основано на:
* MarshalX/yandex-music-api
* Telegram Bot API

Телеграм бот + скачивание всей музыки артиста (по названию), альбома (по share ссылке), плейлиста (по share ссылке), сборника (по share ссылке) с вашего аккаунта на yandex.music.ru. Рекомендуется для работы в паре с медиосервером.
для работы необходимо:
1. Токен вашего яндекс аккаунта
2. Токен телеграмм вашего бота
3. config.py с вашими настройками в папке с программой

# Установка
    1. pip install yandex-music --upgrade
    2. pip install pyTelegramBotAPI
    3. git clone 'THIS_PROJECT'
    4. cd yandex_music_downloader
    5. nano config.py
______________ 
#### config.py

    telegramm_token = "YOUR_TOKEN"
    ya_token = "YOUR_TOKEN"
    download_path = 'YOUR_DOWNLOAD_PATH'
______________

    6. python tbot.py

# Использование
1. Отправьте команду вашему  телеграм боту:


    /download

2. Выберете один из вариантов скачивания, следуйте советом вашего бота.
3. Музыка скачивается в выбранную вами директорию "YOUR_DOWNLOAD_PATH"

Музыка качаются в максимальном доступном качестве до 320 kbps с записанными тегами, обложкой, текстом песни (в тэг и в одноименный файла.txt), если он есть на яндексе.


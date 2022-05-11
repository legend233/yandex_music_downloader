from bs4 import BeautifulSoup
import lxml
import requests
import os

url = input('Введите ссылку, я скачаю: ') + "/albums"
cookie = input('Введите ID сессии. если ничего не введете, то будет использован ID поумолчанию: ')
if cookie == "":
    cookie = "3:1652185258.5.0.1648736560374:xuPOww:1e.1.2:1|289268854.0.2|3:252139.301484.C4XoCGmjV9uME_z9aku8q5tPKyk"
download_path = "'/mnt/raid/nas/music'"
path = "'#artist/#year - #album'"
pattern = "'#number - #title'"
headers = {
    'Accept': '*/*',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36 OPR/85.0.4341.75'
}
req = requests.get(url, headers=headers)
src = req.text
with open("index.html", "w") as file:
    file.write(src)
with open("index.html") as file:
    file_r = file.read()

soup = BeautifulSoup(file_r, "lxml")
all_albums = soup.find_all(class_="d-link deco-link album__caption")
count = 1
for item in all_albums:
    print('Всего альбомов будет скачено:', len(all_albums))
    item_text = item.text
    item_href = "https://music.yandex.ru" + item.get("href")
    os.system(f"perl /home/legend23/application/yandex_music_downloader/app/src/ya.pl -u {item_href} --cookie \"Session_id={cookie}\" --path {path} --bitrate 320 --delay 1 --pattern {pattern} -d {download_path}")
    print(f"{str(count)}. Альбом: {item_text} скачен - link: {item_href}")
    count+=1
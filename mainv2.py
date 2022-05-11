from yandex_music import Client
import os

url = input('Введите ссылку, я скачаю: ')
artist = url.split("/")[-1]
print('artist-id :', artist )
cookie = input('Введите ID сессии. если ничего не введете, то будет использован ID поумолчанию: ')
if cookie == "":
    cookie = "3:1652185258.5.0.1648736560374:xuPOww:1e.1.2:1|289268854.0.2|3:252139.301484.C4XoCGmjV9uME_z9aku8q5tPKyk"


download_path = "'/mnt/raid/nas/music'"
path = "'#artist/#year - #album'"
pattern = "'#number - #title'"

client = Client()
client.init()
albums = client.artistsDirectAlbums(int(artist))

count = 1
for album in albums:
    print('Всего альбомов будет скачено:', len(albums))
    print(album['id'], album['title'])
    os.system(f"perl /home/legend23/application/yandex_music_downloader/app/src/ya.pl -a {album['id']} --cookie \"Session_id={cookie}\" --path {path} --bitrate 320 --delay 1 --pattern {pattern} -d {download_path}")
    print(f"{str(count)}. Альбом: {album['title']} скачен - ID: {album['id']}")
    count+=1

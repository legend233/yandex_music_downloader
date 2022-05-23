from yandex_music import Client
import os
from config import yandex_session_id


def quantity_albums(artist_id):
    client = Client()
    client.init()
    albums = client.artistsDirectAlbums(int(artist_id), page=0, page_size=150, sort_by='year')
    return albums


def quantity_track(album_id):
    client = Client()
    client.init()
    tracks = client.albums_with_tracks(album_id=int(album_id))["track_count"]
    return tracks


def download_artist(artist_id):
    #url = input('Введите ссылку, я скачаю: ')
    print('artist-id :', artist_id)
    #cookie = input('Введите ID сессии. если ничего не введете, то будет использован ID поумолчанию: ')
    cookie = yandex_session_id
    #if cookie == "":
    #    cookie = "3:1652185258.5.0.1648736560374:xuPOww:1e.1.2:1|289268854.0.2|3:252139.301484.C4XoCGmjV9uME_z9aku8q5tPKyk"

    download_path = "'/mnt/raid/nas/music'"
    path = "'#artist/#year - #album'"
    pattern = "'#number - #title'"
    count = 1
    for album in quantity_albums(artist_id):
        print('Всего альбомов будет скачено:', len(quantity_albums(artist_id)))
        print(album['id'], album['title'])
        os.system(f"perl /home/legend23/application/yandex_music_downloader/app/src/ya.pl -a {album['id']} --cookie \"Session_id={cookie}\" --path {path} --bitrate 320 --delay 1 --pattern {pattern} -d {download_path}")
        print(f"{str(count)}. Альбом: {album['title']} скачен - ID: {album['id']}")
        count+=1


def download_album(album_id):
    #url = input('Введите ссылку, я скачаю: ')
    print('artist-id :', album_id)
    #cookie = input('Введите ID сессии. если ничего не введете, то будет использован ID поумолчанию: ')
    cookie = yandex_session_id
    #if cookie == "":
    #    cookie = "3:1652185258.5.0.1648736560374:xuPOww:1e.1.2:1|289268854.0.2|3:252139.301484.C4XoCGmjV9uME_z9aku8q5tPKyk"

    download_path = "'/mnt/raid/nas/music'"
    path = "'#artist/#year - #album'"
    pattern = "'#number - #title'"
    print('Всего треков будет скачено:', quantity_track(album_id))
    os.system(f"perl /home/legend23/application/yandex_music_downloader/app/src/ya.pl -a {album_id} --cookie \"Session_id={cookie}\" --path {path} --bitrate 320 --delay 1 --pattern {pattern} -d {download_path}")
    print(f"Альбом скачен - ID: {album_id}")

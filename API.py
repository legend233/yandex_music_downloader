from yandex_music import Client
from loguru import logger
import requests
import os
import music_tag
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
client = Client(token=os.getenv('YA_TOKEN'))
client.init()
download_path = os.getenv('DOWNLOAD_PATH')

logger.add(f"{download_path}/log.log",
           rotation='00:00', retention='1 week', compression="zip",
           format="{time: DD-MM-YYYY HH:mm:ss} | {level} | {message}",
           )
@logger.catch
def search_and_download_artist(search: str):
    "Ищем лучший результат по запросу артиста и скачиваем все его песни в папку download с разбивкой по альбомам"

    try:
        search_result = client.search(search, type_="artist", page=0, nocorrect=False) # поиск
        artist_id = search_result['artists']['results'][0]['id']
        artist_name = search_result['artists']['results'][0]['name']
    except:
        print('No results! You sure?')
        return f'Твой запрос: {search} не найден.'

    direkt_albums_count = search_result['artists']['results'][0]['counts']['direct_albums']
    artist_echo = f"Start download: Artist ID: {artist_id} / Artist name: {artist_name} / Direct albums: {direkt_albums_count}" # вывод информации о артисте информации по артисту
    logger.info(artist_echo)
    # находим список альбомов артиста с информацией
    direkt_albums = client.artistsDirectAlbums(artist_id=artist_id, page_size=1000)
    # проходимся по каждому альбому
    for album in direkt_albums:
        # проходимся по каждому диску в альбоме и загружаем его в папку
        download_album(album['id'])

    return f"Успешно скачал артиста: {artist_name} с его {direkt_albums_count} альбомами. Наслаждайся музыкой на Plex"

@logger.catch
def get_album_info(album_id):
    album = client.albumsWithTracks(album_id=album_id)
    return f"Скачать альбом '{album['title']}' артиста(ов) \
        '{', '. join([art['name'] for art in album['artists']])}' \
            в котором {album['track_count']} треков?"

@logger.catch
def download_album(album_id):

    album = client.albumsWithTracks(album_id=album_id)
    album_echo = f"Album ID: {album['id']} / Album title - {album['title']}"
    logger.info(album_echo)
    #создаем папку для альбома
    if album['artists'][0]['various']:
        album_folder = f"{download_path}/Various artist/{album['title']} ({album['year']})"
    else:
        artist_id = album['artists'][0]['id']
        artist_name = album['artists'][0]['name']
        artist_cover_link = client.artistsBriefInfo(artist_id=artist_id)['artist']['cover']['uri'].replace('%%',
                                                                                                           '1000x1000')
        artist_folder = f"{download_path}/{artist_name}"
        artist_cover_pic = f"{artist_folder}/artist.jpg"

        os.makedirs(os.path.dirname(f"{artist_folder}/"), exist_ok=True)
        with open(artist_cover_pic, 'wb') as f:  # качаем обложку артиста
            rec = requests.get('http://' + artist_cover_link)
            f.write(rec.content)

        album_folder = f"{artist_folder}/{album['title']} ({album['year']})"

    os.makedirs(os.path.dirname(f"{album_folder}/"),exist_ok=True)
    album_cover_pic = f"{album_folder}/cover.jpg"
    # качаем обложку альбома
    with open(album_cover_pic, 'wb') as f:
        rec = requests.get('http://' + album['cover_uri'].replace('%%', '1000x1000'))
        f.write(rec.content)

    # проходимся по каждому диску в альбоме

    n_volume = 1
    for disk in album['volumes']:
        disk_echo = f"Start download: Volume №: {n_volume} из {len(album['volumes'])}"
        logger.info(disk_echo)
        n_volume += 1

        for track in disk: # проходимся по каждому треку в диске
            track_info = client.tracks_download_info(track_id=track['id'], get_direct_links=True) # узнаем информацию о треке
            track_info.sort(reverse=True, key=lambda key: key['bitrate_in_kbps'])
            track_echo = f"Start Download: ID: {track['id']} {track['title']} bitrate: {track_info[0]['bitrate_in_kbps']} {track_info[1]['direct_link']}"
            logger.info(track_echo)
            tag_info = client.tracks(track['id'])[0]
            info = {
                'title': tag_info['title'],
                'volume_number': track['albums'][0]['track_position']['volume'],
                'total_volumes': len(album['volumes']),
                'track_position': track['albums'][0]['track_position']['index'],
                'total_track': album['track_count'],
                'genre': tag_info['albums'][0]['genre'],
                'artist': ', '. join([art['name'] for art in tag_info['artists']]),
                'album_artist': [artist['name'] for artist in album['artists']],
                'album': album['title'],
            }
            if album['release_date']:
                info['album_year'] = album['release_date'][:10]
            elif album['year']:
                info['album_year'] = album['year']
            else:
                info['album_year'] = ''

            disk_folder = f"{album_folder}/Disk {info['volume_number']}"
            os.makedirs(os.path.dirname(f"{disk_folder}/"), exist_ok=True)
            track_file = f"{disk_folder}/{info['track_position']} - {info['title'].replace('/', '_')}.mp3"
            client.request.download(
                url=track_info[0]['direct_link'],
                filename=track_file
            )
            track_echo_ok = "Track downloaded. Start write tag's."
            logger.info(track_echo_ok)

            #начинаем закачивать тэги в трек
            mp3 = music_tag.load_file(track_file)
            mp3['tracktitle'] = info['title']
            if album['version'] != None:
                mp3['album'] = info['album'] + ' ' + album['version']
            else:
                mp3['album'] = info['album']
            mp3['discnumber'] = info['volume_number']
            mp3['totaldiscs'] = info['total_volumes']
            mp3['tracknumber'] = info['track_position']
            mp3['totaltracks'] = info['total_track']
            mp3['genre'] = info['genre']
            mp3['Year'] = info['album_year']
            if tag_info['version'] != None:
                mp3['comment'] = f"{tag_info['version']} / Release date {info['album_year']}"
            else:
                mp3['comment'] = f"Release date {info['album_year']}"
            mp3['artist'] = info['artist']
            mp3['album_artist'] = info['album_artist']
            try:
                lyrics = client.tracks_lyrics(track_id=track['id'], format='TEXT').fetch_lyrics()
            except:
                lyrics = False
            if lyrics:
                with open(track_file.replace('.mp3', '.txt'), 'w', encoding='UTF8') as text_song:
                    text_song.write(lyrics)
                mp3['lyrics'] = lyrics
            with open(album_cover_pic, 'rb') as img_in:               #ложим картинку в тег "artwork"
                mp3['artwork'] = img_in.read()

            mp3.save()
            tags_echo = "Tag's is writed"
            logger.info(tags_echo)
    return f"Успешно скачал альбом/сборник: {info['album']} с его {info['total_track']} композициями. Наслаждайся музыкой на Plex"

type_to_name = {
    'track': 'трек',
    'artist': 'исполнитель',
    'album': 'альбом',
    'playlist': 'плейлист',
    'video': 'видео',
    'user': 'пользователь',
    'podcast': 'подкаст',
    'podcast_episode': 'эпизод подкаста',
}


def send_search_request_and_print_result(query):
    search_result = client.search(query)

    text = [f'Результаты по запросу "{query}":', '']

    best_result_text = ''
    if search_result.best:
        type_ = search_result.best.type
        best = search_result.best.result

        text.append(f'{type_to_name.get(type_)}')

        if type_ == 'artist':
            best_result_text = best.name

        text.append(f' >>>{best_result_text}<<<')

    if search_result.artists:
        text.append(f"({search_result['artists']['results'][0]['counts']['direct_albums']} - Альбомов)")

    text.append('')
    print('\n'.join(text))

    return ' '.join(text)

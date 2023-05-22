from yandex_music import Client
from loguru import logger
import requests
import os
import music_tag
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
client = Client(token=os.getenv('YA_TOKEN'))
client.init()
download_path = os.getenv('DOWNLOAD_PATH_MUSIC')
folder_audiobooks = os.getenv('DOWNLOAD_PATH_BOOKS')

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

    return f"Успешно скачал артиста: {artist_name} с его {direkt_albums_count} альбомами."

@logger.catch
def get_album_info(album_id):
    album = client.albumsWithTracks(album_id=album_id)
    return f"Альбом:\n'{album['title']}'\nартист:\n'{', '. join([art['name'] for art in album['artists']])}' \
            количество треков: {album['track_count']}"

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
            track_echo = f"Start Download: ID: {track['id']} {track['title']} bitrate: {track_info[0]['bitrate_in_kbps']} {track_info[0]['direct_link']}"
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
    return f"Успешно скачал альбом/сборник: {info['album']} с его {info['total_track']} композициями."


@logger.catch
def get_book_info(album_id):
    book = client.albumsWithTracks(album_id=album_id)
    return f"Аудиокнига:\n{book['title']}\nсодержание из {book['track_count']} частей."


@logger.catch
def download_book(album_id):
    s = client.albumsWithTracks(album_id=album_id)
    info_book = {}

    for i in range(len(s['title'])):
        if s['title'][i] in ',.-:<>;':
            info_book['author'] = s['title'][:i].strip()
            if s['version']:
                info_book['book_title'] = s['title'][i+1:].strip() +' '+ s['version']
            else:
                info_book['book_title'] = s['title'][i+1:].strip()
            break

    info_book['artists'] = ", ".join([x['name'] for x in s['artists']])
    info_book['cover_url'] = 'https://' + s['cover_uri'].replace('%%', '1000x1000')
    info_book['parts'] = s['track_count']
    info_book['labels'] = s['labels'][0]['name']
    info_book['description'] = s['description']
    
    
    book_echo = f"Book ID: {album_id} / Book title - {info_book['book_title']}"
    logger.info(book_echo)
    
    folder_author = f"{folder_audiobooks}/{info_book['author']}"
    folder_book = f"{folder_author}/{info_book['book_title']}/"
    
    os.makedirs(os.path.dirname(folder_book), exist_ok=True)
    file_cover = f"{folder_book}/cover.jpg"
    with open(file_cover, 'wb') as f:
        rec = requests.get(info_book['cover_url'])
        f.write(rec.content)

    volumes = s['volumes']
    for volume in volumes:
        for part in volume:
            # начинаем закачивать треки
            
            print(part['title'], 'ID: ' + part['id'])
            track_info = client.tracks_download_info(track_id=part['id'], get_direct_links=True) # узнаем информацию о треке 
            track_info.sort(reverse=True, key=lambda key: key['bitrate_in_kbps'])
            part_download_link = track_info[0]['direct_link']
            
            part_echo = f"Start Download: ID: {part['id']} {part['title']} bitrate: {track_info[0]['bitrate_in_kbps']} {track_info[0]['direct_link']}"
            logger.info(part_echo)
            
            track_file = f"{folder_book}/{part['albums'][0]['track_position']['index']} - {part['title']}.mp3"
            with open(track_file, 'wb') as f:
                rec = requests.get(part_download_link)
                f.write(rec.content)
            
            track_echo_ok = "Track downloaded. Start write tag's."
            logger.info(track_echo_ok)

            #начинаем закачивать тэги в трек
            mp3 = music_tag.load_file(track_file)
            mp3['tracktitle'] = part['title']
            mp3['album'] = info_book['book_title']
            mp3['discnumber'] = part['albums'][0]['track_position']['volume']
            mp3['tracknumber'] = part['albums'][0]['track_position']['index']
            mp3['totaltracks'] = info_book['parts']
            mp3['genre'] = s['genre']
            mp3['Year'] = s['year']
            mp3['artist'] = info_book['artists']
            mp3['album_artist'] = info_book['artists']
            mp3['comment'] = info_book['description']
            with open(file_cover, 'rb') as img_in:   #ложим картинку в тег "artwork"
                mp3['artwork'] = img_in.read()

            mp3.save() # сохраняем тэги в mp3
            tags_echo = "Tag's is writed"
            logger.info(tags_echo)
    return f"Успешно скачал аудиокнигу: {info_book['book_title']} из {info_book['parts']} частей"


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

        text.append(f'\n{type_to_name.get(type_)}: ')

        if type_ == 'artist':
            best_result_text = best.name

        text.append(f'{best_result_text}')

    if search_result.artists:
        text.append(f"\nВсего альбомов: {search_result['artists']['results'][0]['counts']['direct_albums']}")
    print(' '.join(text))

    return ' '.join(text)



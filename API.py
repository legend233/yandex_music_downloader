from yandex_music import Client
import requests
import os
from mutagen.easyid3 import EasyID3

client = Client(token="AQAAAAARPeR2AAG8XvTIsiSdv0Gav_fZ18vGvzE")
client.init()

def search_and_download(search:str):
    '''Ищем лучший результат по запросу артиста и скачиваем все его песни в папку download с разбивкой по альбомам'''
    download_path = 'download'
    search_result = client.search(search, type_="artist", page=0, nocorrect=False) # поиск
    artist_id = search_result['artists']['results'][0]['id']
    print('Artist ID: ', artist_id) # вывод ID
    print(search_result['artists']['results'][0]['name']) # вывод названия артиста
    print('Direct albums: ',search_result['artists']['results'][0]['counts']['direct_albums']) # вывод количества его альбомов

    direkt_albums = client.artistsDirectAlbums(artist_id=artist_id) # находим список альбомов артистата с информацией

    for album in direkt_albums[0:1]: # проходимся по каждому альбому
        print('id_album: ',album['id'], ' - ', album['title'])
        n_volume = 1
        for disk in client.albumsWithTracks(album_id=album['id'])['volumes']: #проходимся по каждому диску в альбоме
            print('Volume №: ', n_volume)
            n_volume += 1
            for track in disk: # проходимся по каждому треку в диске
                track_info = client.tracks_download_info(track_id=track['id'], get_direct_links=True) # узнаем информацию о треке
                print('ID: ', track['id'], track['title'],'bitrate:', track_info[1]['bitrate_in_kbps'], 'Download: ', track_info[1]['direct_link'])
                info = {
                    'title': client.tracks(track['id'])[0]['title'],
                    'volume_number': client.tracks(track['id'])[0]['albums'][0]['track_position']['volume'],
                    'track_position': client.tracks(track['id'])[0]['albums'][0]['track_position']['index'],
                    'genre': client.tracks(track['id'])[0]['albums'][0]['genre'],
                    'artist': client.artistsBriefInfo(artist_id=artist_id)['artist']['name'],
                    'album': client.tracks(track['id'])[0]['albums'][0]['title'],
                    'album_year': client.tracks(track['id'])[0]['albums'][0]['year'],
                    'artist_cover_link': client.artistsBriefInfo(artist_id=artist_id)['artist']['cover']['uri'].replace('%%', '1000x1000'),
                    'album_cover_link': client.tracks(track['id'])[0]['albums'][0]['cover_uri'].replace('%%', '1000x1000')
                }

                os.makedirs(os.path.dirname(f"{download_path}/{info['artist']}/{info['album']} ({info['album_year']})/Disk {info['volume_number']}/"), exist_ok=True)
                client.request.download(
                    url=track_info[1]['direct_link'],
                    filename=f"{download_path}/{info['artist']}/{info['album']} ({info['album_year']})/Disk {info['volume_number']}/{info['track_position']} - {info['title'].replace('/', '_')}.mp3"
                )


                '''
                mp3 = EasyID3(f"{download_path}/{info['artist']}/{info['album']} ({info['album_year']})/Disk {info['volume_number']}/{info['track_position']} - {info['title'].replace('/', '_')}.mp3")
                mp3['title'] = info['title']
                mp3['album'] = info['album']
                
                mp3.tag.title = info['title']
                mp3.tag.track_num = info['track_position']
                mp3.tag.genre = info['genre']
                mp3.tag.album = info['album']
                mp3.tag = str(info['album_year'])
                mp3.tag.artist = info['artist']
                mp3.tag.title.
                mp3.save()
                print(mp3.get_tags())
                '''

        with open(f"{download_path}/{info['artist']}/{info['album']} ({info['album_year']})/cover.jpg", 'wb') as f:
            rec = requests.get('http://' + info['album_cover_link'])
            f.write(rec.content)

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

        text.append(f'❗️Лучший результат: {type_to_name.get(type_)}')

        if type_ in ['track', 'podcast_episode']:
            artists = ''
            if best.artists:
                artists = ' - ' + ', '.join(artist.name for artist in best.artists)
            best_result_text = best.title + artists
        elif type_ == 'artist':
            best_result_text = best.name
        elif type_ in ['album', 'podcast']:
            best_result_text = best.title
        elif type_ == 'playlist':
            best_result_text = best.title
        elif type_ == 'video':
            best_result_text = f'{best.title} {best.text}'

        text.append(f'Содержимое лучшего результата: {best_result_text}\n')

    if search_result.artists:
        text.append(f'Исполнителей: {search_result.artists.total}')
    if search_result.albums:
        text.append(f'Альбомов: {search_result.albums.total}')
    if search_result.tracks:
        text.append(f'Треков: {search_result.tracks.total}')
    if search_result.playlists:
        text.append(f'Плейлистов: {search_result.playlists.total}')
    if search_result.videos:
        text.append(f'Видео: {search_result.videos.total}')

    text.append('')
    print('\n'.join(text))


if __name__ == '__main__':
    input_query = input('Введите поисковой запрос: ')
    search_and_download(input_query)
from yandex_music import Client
import requests

client = Client(token="AQAAAAARPeR2AAG8XvTIsiSdv0Gav_fZ18vGvzE")
client.init()

def search_and_download(search):
    '''Ищем лучший результат по запросу артиста и скачиваем все его песни'''
    search_result = client.search(search, type_="artist", page=0, nocorrect=False) # поиск
    print(search_result['artists']['results'][0]['id']) # вывод ID
    print(search_result['artists']['results'][0]['name']) # вывод названия артиста
    print('Direct albums: ',search_result['artists']['results'][0]['counts']['direct_albums']) # вывод количества его альбомов

    direkt_albums = client.artistsDirectAlbums(artist_id=search_result['artists']['results'][0]['id']) # находим список альбомов артистата с информацией

    for album in direkt_albums[:1]: # проходимся по каждому альбому
        print('id_album: ',album['id'], ' - ', album['title'])
        n_volume = 1
        for disk in client.albumsWithTracks(album_id=album['id'])['volumes']: #проходимся по каждому диску в альбоме
            print('Volume №: ', n_volume)
            n_volume += 1
            for track in disk: # проходимся по каждому треку в диске
                track_info = client.tracks_download_info(track_id=track['id'], get_direct_links=True) # узнаем информацию о треке
                print('ID: ', track['id'], track['title'],'bitrate:', track_info[1]['bitrate_in_kbps'], 'Download: ', track_info[1]['direct_link'])
                #client.request.download(url=track_info[1]['direct_link'], filename=f"download/{}{track['title']}.mp3")
                print(client.tracks(track['id']))
                info = {
                    'title' : client.tracks(track['id'])[0]['title'],
                    'track_position': client.tracks(track['id'])[0]['albums'][0]['track_position']['index'],
                    'genre' : client.tracks(track['id'])[0]['albums'][0]['genre'],
                    'artist' : client.tracks(track['id'])[0]['artists'][0]['name'],
                    'album' : client.tracks(track['id'])[0]['albums'][0]['title'],
                    'album_year': client.tracks(track['id'])[0]['albums'][0]['year'],
                    'album_cover_link': client.tracks(track['id'])[0]['artists'][0]['cover']['uri'].replace('%%', '1000x1000')
                }
                print(info)
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
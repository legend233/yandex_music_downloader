from yandex_music import Client

#client = Client(token="Sessionid=3:1652185258.5.0.1648736560374:xuPOww:1e.1.2:1|289268854.0.2|3:252139.301484.C4XoCGmjV9uME_z9aku8q5tPKyk")
client = Client()
client.init()

albums_all = []
albums = client.artistsDirectAlbums(10731)
for album in albums:
    print(album['id'], album['title'])

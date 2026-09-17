"""Изолированные тесты: API.py не импортируется и клиент не создаётся."""
import ast
from pathlib import Path
from types import SimpleNamespace as Model
import unittest
from unittest.mock import Mock, call


FUNCTIONS = {'search_artists', 'get_artist_info', 'download_artist',
             'search_and_download_artist'}


def load_functions(client, download_album):
    path = Path(__file__).resolve().parents[1] / 'API.py'
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS]
    assert {node.name for node in functions} == FUNCTIONS
    for node in functions:
        node.decorator_list = []
    namespace = {'client': client, 'logger': Mock(), 'download_album': download_album}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


def albums(*ids):
    return Model(albums=[Model(id=album_id) for album_id in ids])


class ArtistApiTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock(spec=['search', 'artists_brief_info', 'artists_direct_albums'])
        self.client.artists_brief_info.return_value = Model(
            artist=Model(id=42, name='Artist', counts=Model(direct_albums=999)))
        self.download_album = Mock(return_value='Альбом скачан')
        self.api = load_functions(self.client, self.download_album)

    def test_search_returns_plain_dicts_and_forwards_page(self):
        self.client.search.return_value = Model(artists=Model(results=[
            Model(id=42, name='Artist'), Model(id='43', name='Artist')]))
        self.assertEqual(self.api['search_artists']('query', page=3), [
            {'id': 42, 'name': 'Artist'}, {'id': '43', 'name': 'Artist'}])
        self.client.search.assert_called_once_with(
            'query', type_='artist', page=3, nocorrect=False)
        self.download_album.assert_not_called()

    def test_search_empty_results(self):
        for result in (None, Model(artists=None), Model(artists=Model(results=[])),
                       Model(artists=Model(results=None))):
            with self.subTest(result=result):
                self.client.search.return_value = result
                self.assertEqual(self.api['search_artists']('missing'), [])

    def test_search_error_is_not_hidden_as_empty_results(self):
        self.client.search.side_effect = RuntimeError('offline')
        with self.assertRaises(RuntimeError):
            self.api['search_artists']('query')

    def test_info_by_id(self):
        self.assertEqual(self.api['get_artist_info'](42),
                         'Артист: Artist\nID: 42\nПрямых альбомов: 999')
        self.client.artists_brief_info.assert_called_once_with(artist_id=42)
        self.client.search.assert_not_called()

    def test_info_without_counts(self):
        self.client.artists_brief_info.return_value.artist.counts = None
        self.assertEqual(self.api['get_artist_info']('42'), 'Артист: Artist\nID: 42')

    def test_missing_artist(self):
        for brief in (None, Model(artist=None)):
            self.client.artists_brief_info.return_value = brief
            for name in ('get_artist_info', 'download_artist'):
                with self.subTest(brief=brief, function=name):
                    self.assertIn('не найден', self.api[name](42))
        self.download_album.assert_not_called()
        self.client.artists_direct_albums.assert_not_called()

    def test_all_pages_and_deduplication_without_name_search(self):
        # Даже короткая страница и страница только с дублями не завершают обход.
        self.client.artists_direct_albums.side_effect = [
            albums(1, 1, 2), albums('1', '2'), albums(3), albums()]
        result = self.api['download_artist']('42')
        self.assertEqual(result, 'Успешно скачал артиста: Artist с его 3 альбомами.')
        self.assertEqual(self.download_album.call_args_list, [call(1), call(2), call(3)])
        self.assertEqual(self.client.artists_direct_albums.call_args_list, [
            call(artist_id='42', page=page, page_size=100) for page in range(4)])
        self.client.search.assert_not_called()

    def test_empty_discography(self):
        self.client.artists_direct_albums.return_value = albums()
        self.assertIn('нет прямых альбомов', self.api['download_artist'](42))
        self.download_album.assert_not_called()

    def test_suppressed_and_raised_album_errors_continue_download(self):
        self.client.artists_direct_albums.side_effect = [albums(1, 2, 3), albums()]
        self.download_album.side_effect = [None, RuntimeError('failed'), 'ok']
        result = self.api['download_artist'](42)
        self.assertNotIn('Успешно', result)
        self.assertIn('Скачано альбомов: 1; не удалось скачать: 2', result)
        self.assertEqual(self.download_album.call_args_list, [call(1), call(2), call(3)])

    def test_all_albums_fail(self):
        self.client.artists_direct_albums.side_effect = [albums(1), albums()]
        self.download_album.return_value = None
        result = self.api['download_artist'](42)
        self.assertNotIn('Успешно', result)
        self.assertIn('Скачано альбомов: 0; не удалось скачать: 1', result)

    def test_page_errors_report_incomplete_download(self):
        for failure in (None, RuntimeError('offline')):
            with self.subTest(failure=failure):
                self.client.artists_direct_albums.side_effect = [albums(1), failure]
                result = self.api['download_artist'](42)
                self.assertNotIn('Успешно', result)
                self.assertIn('не завершена', result)
                self.assertIn('Скачано альбомов: 1', result)

    def test_brief_info_error(self):
        self.client.artists_brief_info.side_effect = RuntimeError('offline')
        self.assertIn('не завершена', self.api['download_artist'](42))
        self.download_album.assert_not_called()

    def test_compatibility_wrapper_uses_first_id(self):
        self.api['search_artists'] = Mock(return_value=[
            {'id': 42, 'name': 'Artist'}, {'id': 43, 'name': 'Artist'}])
        self.api['download_artist'] = Mock(return_value='Загрузка с ошибками')
        self.assertEqual(self.api['search_and_download_artist']('query'), 'Загрузка с ошибками')
        self.api['search_artists'].assert_called_once_with('query')
        self.api['download_artist'].assert_called_once_with(42)

    def test_compatibility_wrapper_no_results_or_search_error(self):
        self.api['download_artist'] = Mock()
        for search in (Mock(return_value=[]), Mock(side_effect=RuntimeError('offline'))):
            self.api['search_artists'] = search
            self.assertEqual(self.api['search_and_download_artist']('query'),
                             'Твой запрос: query не найден.')
        self.api['download_artist'].assert_not_called()


if __name__ == '__main__':
    unittest.main()
